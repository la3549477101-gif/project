package com.example.odmtracker;

import java.math.*;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.text.Normalizer;
import java.time.*;
import java.util.*;
import java.util.stream.Collectors;
import org.springframework.data.domain.*;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service @Transactional
public class SalesOrderService {
    private final SalesOrderRepository orders;
    private final CustomerRepository customers;
    private final ProjectRepository projects;
    private final ProjectDetailRepository details;
    private final ChangeRepository changes;
    public SalesOrderService(SalesOrderRepository orders,CustomerRepository customers,ProjectRepository projects,ProjectDetailRepository details,ChangeRepository changes) {
        this.orders=orders;this.customers=customers;this.projects=projects;this.details=details;this.changes=changes;
    }
    public record LineInput(Long detailId,BigDecimal quantity,String unit,BigDecimal unitPrice,LocalDate expectedDeliveryDate,String notes) {}
    public record OrderInput(String requestKey,Long customerId,String customerOrderNo,LocalDate orderDate,String purpose,String currency,String source,String notes,List<LineInput> lines,String reviewHash) {}
    public record LineView(Long id,Long projectId,Long detailId,String projectName,String materialModel,String specification,String quantity,String unit,String unitPrice,String amount,LocalDate expectedDeliveryDate,String notes) {}
    public record OrderView(Long id,String internalNumber,Long customerId,String customerName,String customerOrderNo,LocalDate orderDate,String purpose,String currency,String totalAmount,String taxBasis,String calculationRule,String source,String notes,Instant createdAt,Map<String,String> termsSnapshot,List<LineView> lines,String reviewHash) {}
    public record Summary(Long id,String internalNumber,Long customerId,String customerName,String customerOrderNo,LocalDate orderDate,String purpose,String currency,String totalAmount,int lineCount) {}
    public record Total(String currency,String amount,long orderCount) {}
    private record Prepared(OrderInput input,String hash) {}
    private static final List<String> TERM_KEYS=List.of("ourCompany","tradeMethod","paymentCondition","creditLimit","extraTerms","reconciliationCycle","reconciliationDate","invoiceDate","taxIncluded");

    private static String text(String value,int max,String label) {
        String result=value==null?"":value.trim();
        if(result.length()>max) throw bad(label+"不能超过"+max+"字");
        return result;
    }
    private static void date(LocalDate value,boolean required,String label) {
        if(value==null) {if(required) throw bad("请填写"+label);return;}
        if(value.getYear()<1||value.getYear()>9999) throw bad(label+"年份须在1到9999之间");
    }
    private static BigDecimal number(BigDecimal value,boolean positive,String label) {
        if(value==null) throw bad("请填写"+label);
        BigDecimal normalized=value.stripTrailingZeros();
        if(value.signum()<0 || positive&&value.signum()==0 || normalized.scale()>6 || (long)normalized.precision()-normalized.scale()>13)
            throw bad(label+"须为"+(positive?"大于0的数":"非负数")+"，最多13位整数和6位小数");
        return value.setScale(6);
    }
    private static String decimal(BigDecimal value) {return value.stripTrailingZeros().toPlainString();}
    private static String amount(BigDecimal value) {return value.setScale(2).toPlainString();}
    private static String digest(List<String> values) {
        String canonical=values.stream().map(v->v.length()+":"+v).collect(Collectors.joining());
        try {return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(canonical.getBytes(StandardCharsets.UTF_8)));}
        catch(NoSuchAlgorithmException e) {throw new IllegalStateException(e);}
    }
    private Prepared prepare(OrderInput input) {
        if(input==null||input.customerId()==null||input.customerId()<=0) throw bad("请选择采购客户");
        String key=text(input.requestKey(),36,"请求编号");
        try {if(!UUID.fromString(key).toString().equalsIgnoreCase(key)) throw new IllegalArgumentException();}
        catch(IllegalArgumentException e) {throw bad("请求编号无效，请重新打开新建订单");}
        key=key.toLowerCase(Locale.ROOT);
        String orderNo=text(input.customerOrderNo(),100,"客户订单号");
        date(input.orderDate(),true,"下单日期");
        if(!List.of("SAMPLE","MASS_PRODUCTION").contains(input.purpose()==null?"":input.purpose())) throw bad("请选择样品单或量产单");
        String currency=text(input.currency(),3,"币种").toUpperCase(Locale.ROOT);
        try {if(!currency.matches("[A-Z]{3}")) throw new IllegalArgumentException();Currency.getInstance(currency);}
        catch(IllegalArgumentException e) {throw bad("请填写有效的三位币种代码，例如CNY或USD");}
        String source=text(input.source(),1000,"订单依据");
        if(source.isEmpty()) throw bad("请填写已确认采购的订单依据，不能把意向当作订单");
        String notes=text(input.notes(),2000,"订单备注");
        if(input.lines()==null||input.lines().isEmpty()||input.lines().size()>200) throw bad("每单请选择1到200项型号规格");
        Set<Long> ids=new HashSet<>();List<LineInput> lines=new ArrayList<>();
        List<String> canonical=new ArrayList<>(List.of(input.customerId().toString(),orderNo,input.orderDate().toString(),input.purpose(),currency,source,notes));
        for(LineInput row:input.lines()) {
            if(row==null||row.detailId()==null||row.detailId()<=0||!ids.add(row.detailId())) throw bad("请选择有效且不重复的型号规格");
            String unit=text(row.unit(),30,"数量单位");if(unit.isEmpty()) throw bad("请填写每项的数量及计价单位");
            BigDecimal quantity=number(row.quantity(),true,"本次数量"), price=number(row.unitPrice(),false,"含税成交单价");
            date(row.expectedDeliveryDate(),false,"约定交期");
            String lineNotes=text(row.notes(),1000,"明细备注");
            lines.add(new LineInput(row.detailId(),quantity,unit,price,row.expectedDeliveryDate(),lineNotes));
            canonical.addAll(List.of(row.detailId().toString(),decimal(quantity),unit,decimal(price),row.expectedDeliveryDate()==null?"":row.expectedDeliveryDate().toString(),lineNotes));
        }
        return new Prepared(new OrderInput(key,input.customerId(),orderNo,input.orderDate(),input.purpose(),currency,source,notes,lines,input.reviewHash()),digest(canonical));
    }
    private Optional<OrderView> retry(Prepared prepared) {
        return orders.findByRequestKey(prepared.input().requestKey()).map(existing->{
            if(!existing.requestHash.equals(prepared.hash())) throw conflict("本次请求已保存过其他内容，请打开原订单核对后重新新建");
            return view(existing,null);
        });
    }
    private SalesOrder build(Prepared prepared,boolean lock) {
        OrderInput input=prepared.input();
        CustomerRecord customer=(lock?customers.findLockedById(input.customerId()):customers.findById(input.customerId()))
            .orElseThrow(()->bad("所选客户不存在"));
        String numberKey=input.customerOrderNo().isEmpty()?null:digest(List.of(Normalizer.normalize(input.customerOrderNo(),Normalizer.Form.NFKC).toLowerCase(Locale.ROOT)));
        if(numberKey!=null&&orders.existsByCustomerIdAndOrderNumberKey(customer.id,numberKey)) throw conflict("该客户已存在相同客户订单号，请核对原订单");
        List<Long> ids=input.lines().stream().map(LineInput::detailId).toList();
        List<Long> projectIds=details.projectIds(ids).stream().sorted().toList();
        if(projectIds.size()>1) throw bad("当前一张订单仅支持同一项目的多个型号规格，请按项目分别建单");
        Map<Long,ProjectRecord> projectMap=new HashMap<>();
        for(Long id:projectIds) {
            ProjectRecord p=(lock?projects.findLockedById(id):projects.findById(id)).orElseThrow(()->bad("订单关联的项目已不存在"));
            if(!Objects.equals(p.customerId,customer.id)) throw bad("项目不属于当前采购客户，请先核对公司归属");
            projectMap.put(id,p);
        }
        Map<Long,ProjectDetail> byId=new HashMap<>();details.findAllById(ids).forEach(d->byId.put(d.id,d));
        SalesOrder order=new SalesOrder();
        order.customerId=customer.id;order.customerName=customer.fullName;order.customerOrderNo=input.customerOrderNo();order.orderNumberKey=numberKey;
        order.requestKey=input.requestKey();order.requestHash=prepared.hash();order.orderDate=input.orderDate();order.purpose=input.purpose();order.currency=input.currency();
        order.source=input.source();order.notes=input.notes();order.totalAmount=BigDecimal.ZERO.setScale(2);
        for(String key:TERM_KEYS) if(customer.profile!=null&&customer.profile.containsKey(key)) order.termsSnapshot.put(key,customer.profile.get(key));
        for(LineInput inputLine:input.lines()) {
            ProjectDetail d=byId.get(inputLine.detailId());
            if(d==null) throw bad("所选型号规格已不存在，请重新选择");
            if(d.archived) throw conflict("所选明细已归档，请先恢复后再建单");
            ProjectRecord p=projectMap.get(d.projectId);if(p==null) throw bad("型号规格的项目归属已变化，请重新选择");
            SalesOrderLine row=new SalesOrderLine();row.projectId=p.getId();row.detailId=d.id;row.projectName=p.getProjectName();row.materialModel=d.materialModel;row.specification=d.specification;
            row.quantity=inputLine.quantity();row.unit=inputLine.unit();row.unitPrice=inputLine.unitPrice();
            row.amount=row.quantity.multiply(row.unitPrice).setScale(2,RoundingMode.HALF_UP);
            row.expectedDeliveryDate=inputLine.expectedDeliveryDate();row.notes=inputLine.notes();
            order.lines.add(row);order.totalAmount=order.totalAmount.add(row.amount);
        }
        return order;
    }
    private String reviewHash(SalesOrder order) {
        List<String> parts=new ArrayList<>(List.of(order.requestHash,order.customerName,amount(order.totalAmount)));
        order.termsSnapshot.entrySet().stream().sorted(Map.Entry.comparingByKey()).forEach(e->{parts.add(e.getKey());parts.add(e.getValue());});
        for(SalesOrderLine row:order.lines) parts.addAll(List.of(row.projectId.toString(),row.projectName,row.materialModel,row.specification));
        return digest(parts);
    }
    public OrderView preview(OrderInput input) {
        Prepared prepared=prepare(input);
        Optional<OrderView> existing=retry(prepared);if(existing.isPresent()) return existing.get();
        SalesOrder order=build(prepared,false);
        return view(order,reviewHash(order));
    }
    public OrderView create(OrderInput input) {
        Prepared prepared=prepare(input);
        Optional<OrderView> existing=retry(prepared);if(existing.isPresent()) return existing.get();
        if(input.reviewHash()==null||!input.reviewHash().matches("[0-9a-f]{64}")) throw conflict("请先核对订单预览，再确认保存");
        // Serialize same-customer submissions, and recheck the key after acquiring the lock.
        customers.findLockedById(input.customerId()).orElseThrow(()->bad("所选客户不存在"));
        existing=retry(prepared);if(existing.isPresent()) return existing.get();
        SalesOrder order=build(prepared,true);
        if(!input.reviewHash().equals(reviewHash(order))) throw conflict("客户条款或型号资料已变化，请重新预览核对后保存");
        order.createdAt=Instant.now();orders.saveAndFlush(order);
        ChangeRecord event=new ChangeRecord();event.occurredAt=order.createdAt;event.customerId=order.customerId;event.customerName=order.customerName;
        event.objectName=internalNumber(order);event.entityType="ORDER";event.action="NEW";
        event.detail=(order.purpose.equals("SAMPLE")?"样品订单":"量产订单")+"；"+order.lines.size()+"项明细；含税总额："+amount(order.totalAmount)+" "+order.currency+"；按下单时客户条件保存快照";
        changes.save(event);
        return view(order,null);
    }
    private String internalNumber(SalesOrder order) {return order.id==null?"待保存":String.format(Locale.ROOT,"SO-%08d",order.id);}
    private OrderView view(SalesOrder order,String hash) {
        List<LineView> rows=order.lines.stream().map(r->new LineView(r.id,r.projectId,r.detailId,r.projectName,r.materialModel,r.specification,decimal(r.quantity),r.unit,decimal(r.unitPrice),amount(r.amount),r.expectedDeliveryDate,r.notes)).toList();
        return new OrderView(order.id,internalNumber(order),order.customerId,order.customerName,order.customerOrderNo,order.orderDate,order.purpose,order.currency,amount(order.totalAmount),order.taxBasis,order.calculationRule,order.source,order.notes,order.createdAt,new LinkedHashMap<>(order.termsSnapshot),rows,hash);
    }
    public OrderView get(Long id) {return view(orders.findById(id).orElseThrow(()->new ResponseStatusException(HttpStatus.NOT_FOUND,"订单不存在")),null);}
    public Map<String,Object> list(Long customerId,int page,int size) {
        if(customerId!=null&&(customerId<=0||!customers.existsById(customerId))) throw bad("所选客户不存在");
        if(page<0||size<1||size>50) throw bad("订单分页参数无效");
        Page<SalesOrder> result=orders.search(customerId,PageRequest.of(page,size,Sort.by(Sort.Order.desc("orderDate"),Sort.Order.desc("id"))));
        List<Summary> items=result.stream().map(o->new Summary(o.id,internalNumber(o),o.customerId,o.customerName,o.customerOrderNo,o.orderDate,o.purpose,o.currency,amount(o.totalAmount),o.lines.size())).toList();
        List<Total> totals=orders.totals(customerId).stream().map(t->new Total(t.getCurrency(),amount(t.getAmount()),t.getOrderCount())).toList();
        return Map.of("items",items,"total",result.getTotalElements(),"page",page,"size",size,"totals",totals);
    }
    public String export(Long customerId) {
        if(customerId!=null&&(customerId<=0||!customers.existsById(customerId))) throw bad("所选客户不存在");
        StringBuilder csv=new StringBuilder("\uFEFF");
        appendCsv(csv,List.of("内部订单号","客户订单号","客户名称","下单日期","订单用途","币种","订单含税总额","项目名称","材料型号","成品规格","本次数量","单位","含税成交单价","明细含税金额","约定交期","订单依据","订单备注","明细备注"));
        int page=0;Page<SalesOrder> batch;
        do {
            batch=orders.search(customerId,PageRequest.of(page++,100,Sort.by(Sort.Order.asc("id"))));
            for(SalesOrder o:batch) {
                boolean first=true;
                for(SalesOrderLine r:o.lines) {
                    appendCsv(csv,Arrays.asList(internalNumber(o),o.customerOrderNo,o.customerName,o.orderDate.toString(),o.purpose.equals("SAMPLE")?"样品单":"量产单",o.currency,first?amount(o.totalAmount):"",r.projectName,r.materialModel,r.specification,decimal(r.quantity),r.unit,decimal(r.unitPrice),amount(r.amount),r.expectedDeliveryDate==null?"":r.expectedDeliveryDate.toString(),o.source,o.notes,r.notes));
                    first=false;
                }
            }
        } while(batch.hasNext());
        return csv.toString();
    }
    private void appendCsv(StringBuilder csv,List<String> cells) {
        csv.append(cells.stream().map(value->{
            String s=value==null?"":value;
            if(s.stripLeading().matches("(?s)^[=+@-].*")||s.startsWith("\t")||s.startsWith("\r")) s="'"+s;
            return "\""+s.replace("\"","\"\"")+"\"";
        }).collect(Collectors.joining(","))).append("\r\n");
    }
    private static ResponseStatusException bad(String message) {return new ResponseStatusException(HttpStatus.BAD_REQUEST,message);}
    private static ResponseStatusException conflict(String message) {return new ResponseStatusException(HttpStatus.CONFLICT,message);}
}
