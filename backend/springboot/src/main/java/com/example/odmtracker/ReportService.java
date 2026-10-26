package com.example.odmtracker;

import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.ObjectMapper;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.LocalDate;
import java.util.*;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class ReportService {
    public static final List<String> KEYS=List.of("owner","reportDate","productLine","caseStatus","customerName","terminalCustomer","projectName","application","materialModel","specification","quotePrice","estimatedAnnualQuantity","estimatedAnnualRevenue","statusNote","expectedMpText","competitor","competitorPrice","notes");
    public static final List<String> LABELS=List.of("负责人","日期","产品线","案子状况","客户","终端客户","项目名称","应用","材料型号","成品规格","单价","预估年用量","预估年营业额","项目状态","预估量产时间","竞争对手","竞争对手单价","备注");
    private final ProjectRepository projects; private final ProjectDetailRepository details;
    private final WorkspaceService workspace; private final ProjectBusinessService business; private final ObjectMapper mapper;
    public ReportService(ProjectRepository projects,ProjectDetailRepository details,WorkspaceService workspace,ProjectBusinessService business,ObjectMapper mapper) {
        this.projects=projects;this.details=details;this.workspace=workspace;this.business=business;this.mapper=mapper;
    }
    public record Row(String key,Long projectId,Long detailId,Long customerId,boolean important,boolean archivedOnly,String category,Map<String,String> fields,String currency,String quantityUnit,String priceTerms,String businessStage,String version) {}
    public record Input(String version,Long detailId,Long customerId,Boolean important,String category,Map<String,String> fields,String currency,String quantityUnit,String priceTerms,String businessStage) {}
    private static String text(Object value) {return value==null?"":value.toString().trim();}
    private static String canonical(String value) {return value.replaceAll("\\s+","").replace('（','(').replace('）',')').replace("单价(含税)元","单价").replace("单价(含税)","单价");}
    private Map<String,Object> metadata(ProjectRecord p) {
        if(p.getReportData()==null||p.getReportData().isBlank()) return new LinkedHashMap<>();
        try {Map<String,Object> data=mapper.readValue(p.getReportData(),new TypeReference<LinkedHashMap<String,Object>>(){});if(!(data.get("fields") instanceof Map)) throw new IllegalArgumentException();return data;}
        catch(Exception e) {throw bad("项目原报告资料格式异常，请先检查，未忽略或清除原数据");}
    }
    private Map<String,String> legacyFields(Map<String,Object> meta) {
        Map<String,String> raw=new LinkedHashMap<>();
        if(meta.get("fields") instanceof Map<?,?> f) f.forEach((k,v)->raw.put(canonical(k.toString()),text(v)));
        Map<String,String> result=new LinkedHashMap<>();
        for(int i=0;i<KEYS.size();i++) result.put(KEYS.get(i),raw.getOrDefault(canonical(LABELS.get(i)),""));
        return result;
    }
    private static String decimal(BigDecimal value) {return value==null?"":value.stripTrailingZeros().toPlainString();}
    private String category(ProjectDetail d,Map<String,Object> meta) {
        String value=d==null?text(meta.getOrDefault("reportCategory",meta.get("sheet"))):text(d.reportCategory);
        return List.of("开发","成交","EOL").contains(value)?value:"开发";
    }
    private String version(ProjectRecord p,ProjectDetail d,Map<String,String> fields,String category) {
        try {String value=mapper.writeValueAsString(Arrays.asList(p.customerId,p.isImportant(),p.getReportData(),fields,category,d));
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));}
        catch(Exception e) {throw new IllegalStateException(e);}
    }
    private Row row(ProjectRecord p,ProjectDetail d) {return row(p,d,false);}
    private Row row(ProjectRecord p,ProjectDetail d,boolean archivedOnly) {
        Map<String,Object> meta=metadata(p);Map<String,String> fields=legacyFields(meta);
        fields.put("projectName",text(p.getProjectName()));fields.put("terminalCustomer",text(p.getTerminalCustomer()));fields.put("application",text(p.getApplication()));
        if(p.customerId!=null) fields.put("customerName",workspace.customer(p.customerId).fullName);
        if(d==null&&p.getExpectedMpDate()!=null) fields.put("expectedMpText",p.getExpectedMpDate().toString());
        if(d!=null) {
            fields.put("owner",text(d.owner));fields.put("reportDate",text(d.reportDate));fields.put("productLine",text(d.productLine));fields.put("caseStatus",text(d.caseStatus));
            fields.put("materialModel",text(d.materialModel));fields.put("specification",text(d.specification));fields.put("quotePrice",decimal(d.quotePrice));
            fields.put("estimatedAnnualQuantity",decimal(d.estimatedAnnualQuantity));fields.put("estimatedAnnualRevenue",decimal(d.estimatedAnnualRevenue));
            fields.put("statusNote",text(d.statusNote));fields.put("expectedMpText",text(d.expectedMpText));fields.put("competitor",text(d.competitor));fields.put("competitorPrice",decimal(d.competitorPrice));fields.put("notes",text(d.notes));
        }
        String category=category(d,meta);
        if(archivedOnly) {for(String key:List.of("materialModel","specification","quotePrice","estimatedAnnualQuantity","estimatedAnnualRevenue","competitorPrice"))fields.put(key,"");fields.put("statusNote","全部型号规格已归档，可在“规格与跟进”中恢复；本行为项目入口，不计作活动报价明细。");}
        String legacyTerms=text(meta.get("priceTerms"));
        if(!meta.containsKey("priceTerms")&&legacyTerms.isEmpty()&&meta.get("fields") instanceof Map<?,?> raw&&raw.keySet().stream().anyMatch(k->canonical(k.toString()).equals("单价")&&k.toString().contains("含税"))) legacyTerms="含税（原表表头）";
        return new Row((d==null?"p:":"d:")+(d==null?p.getId():d.id),p.getId(),d==null?null:d.id,p.customerId,p.isImportant(),archivedOnly,category,fields,d==null?text(meta.get("currency")):text(d.currency),d==null?text(meta.get("quantityUnit")):text(d.quantityUnit),d==null?legacyTerms:text(d.priceTerms),d==null?text(meta.get("businessStage")):text(d.businessStage),version(p,d,fields,category));
    }
    @Transactional(readOnly=true)
    public List<Row> list() {
        Map<Long,List<ProjectDetail>> byProject=new HashMap<>();details.findAll().forEach(d->byProject.computeIfAbsent(d.projectId,k->new ArrayList<>()).add(d));
        List<Row> rows=new ArrayList<>();
        for(ProjectRecord p:projects.findAll()) {
            List<ProjectDetail> own=byProject.getOrDefault(p.getId(),List.of());
            if(own.isEmpty()) rows.add(row(p,null));
            else if(own.stream().allMatch(d->d.archived)) rows.add(row(p,null,true));
            else own.stream().filter(d->!d.archived).sorted(Comparator.comparing(d->d.id)).forEach(d->rows.add(row(p,d)));
        }
        rows.sort(Comparator.comparing((Row r)->r.fields().get("customerName")).thenComparing(r->r.fields().get("projectName")).thenComparing(Row::projectId).thenComparing(Row::key));
        return rows;
    }
    private Map<String,String> fields(Input input) {
        if(input==null||input.fields()==null) throw bad("报告行内容不能为空");
        Map<String,String> result=new LinkedHashMap<>();
        for(int i=0;i<KEYS.size();i++) {String key=KEYS.get(i),value=text(input.fields().get(key));int max=List.of("statusNote","notes").contains(key)?2000:List.of("reportDate","expectedMpText").contains(key)?100:255;
            if(value.length()>max) throw bad(LABELS.get(i)+"不能超过"+max+"字");result.put(key,value);}
        if(result.get("projectName").isBlank()||result.get("projectName").equals("/")) throw bad("请填写项目名称");
        if(!List.of("开发","成交","EOL").contains(text(input.category()))) throw bad("请选择开发、成交或EOL分类");
        if(text(input.currency()).length()>30||text(input.quantityUnit()).length()>30||text(input.priceTerms()).length()>255)throw bad("币种及单位最多30字，计价说明最多255字");
        if(!text(input.businessStage()).isEmpty()&&!ProjectBusinessService.STAGES.contains(text(input.businessStage())))throw bad("业务交易阶段无效，请重新选择");
        return result;
    }
    private BigDecimal decimal(String value,String label) {
        if(value.isEmpty()) return null;
        try {return new BigDecimal(value);} catch(NumberFormatException e) {throw bad(label+"请填写数值；未知请留空，文字说明放在备注");}
    }
    private ProjectDetail detail(Input input,Map<String,String> f,ProjectDetail old) {
        ProjectDetail d=old==null?new ProjectDetail():mapper.convertValue(old,ProjectDetail.class);
        d.owner=f.get("owner");d.reportDate=f.get("reportDate");d.productLine=f.get("productLine");d.caseStatus=f.get("caseStatus");d.reportCategory=text(input.category());
        d.materialModel=f.get("materialModel");d.specification=f.get("specification");d.quotePrice=decimal(f.get("quotePrice"),"单价");
        d.estimatedAnnualQuantity=decimal(f.get("estimatedAnnualQuantity"),"预估年用量");d.estimatedAnnualRevenue=decimal(f.get("estimatedAnnualRevenue"),"预估年营业额");
        d.statusNote=f.get("statusNote");d.expectedMpText=f.get("expectedMpText");d.competitor=f.get("competitor");d.competitorPrice=decimal(f.get("competitorPrice"),"竞争对手单价");d.notes=f.get("notes");
        d.currency=text(input.currency());d.quantityUnit=text(input.quantityUnit());d.priceTerms=text(input.priceTerms());d.businessStage=text(input.businessStage());return d;
    }
    @Transactional
    public Row save(Long id,Input input) {
        Map<String,String> f=fields(input);
        ProjectRecord p=id==null?new ProjectRecord():projects.findLockedById(id).orElseThrow(()->new ResponseStatusException(HttpStatus.NOT_FOUND,"项目不存在"));
        ProjectDetail d=null;
        if(input.detailId()!=null) {
            d=details.findById(input.detailId()).orElseThrow(()->bad("型号规格不存在"));
            if(!Objects.equals(d.projectId,id)||d.archived) throw bad("型号规格不属于当前项目或已归档");
        } else if(id!=null&&!details.findByProjectIdOrderByIdAsc(id).isEmpty()) throw new ResponseStatusException(HttpStatus.CONFLICT,"项目已维护型号规格，请刷新主表后编辑对应明细");
        Row before=id==null?null:row(p,d);
        if(before!=null&&!Objects.equals(before.version(),input.version())) throw new ResponseStatusException(HttpStatus.CONFLICT,"资料已发生变化，请关闭编辑并刷新后重新核对");
        if(input.customerId()!=null) {workspace.customer(input.customerId());f.put("customerName",workspace.customer(input.customerId()).fullName);}
        boolean important=Boolean.TRUE.equals(input.important());
        if(before!=null&&before.fields().equals(f)&&Objects.equals(before.customerId(),input.customerId())&&before.important()==important&&before.category().equals(input.category())&&before.currency().equals(text(input.currency()))&&before.quantityUnit().equals(text(input.quantityUnit()))&&before.priceTerms().equals(text(input.priceTerms()))&&before.businessStage().equals(text(input.businessStage()))) return before;
        boolean createDetail=id==null&&(!f.get("materialModel").isEmpty()||!f.get("specification").isEmpty());
        ProjectDetail prepared=d!=null||createDetail?detail(input,f,d):null;
        ProjectRecord projectInput=mapper.convertValue(p,ProjectRecord.class);
        projectInput.customerId=input.customerId();projectInput.setProjectName(f.get("projectName"));projectInput.setTerminalCustomer(f.get("terminalCustomer"));projectInput.setApplication(f.get("application"));
        if(d!=null&&input.customerId()==null) {
            Map<String,Object> meta=metadata(p);Map<String,Object> raw=new LinkedHashMap<>();if(meta.get("fields") instanceof Map<?,?> old)old.forEach((k,v)->raw.put(k.toString(),v));
            String key=raw.keySet().stream().filter(k->canonical(k).equals("客户")).findFirst().orElse("客户");
            if(!text(raw.get(key)).equals(f.get("customerName"))) {raw.put(key,f.get("customerName"));meta.put("fields",raw);String json=mapper.writeValueAsString(meta);if(json.length()>64000)throw bad("报告资料过长，请缩短备注");projectInput.setReportData(json);}
        }
        if(d==null) {
            Map<String,Object> meta=metadata(p);Map<String,Object> raw=new LinkedHashMap<>();if(meta.get("fields") instanceof Map<?,?> old) old.forEach((k,v)->raw.put(k.toString(),v));
            for(int i=0;i<KEYS.size();i++) {
                if(KEYS.get(i).equals("customerName")&&input.customerId()!=null) continue;
                String label=LABELS.get(i),key=raw.keySet().stream().filter(k->canonical(k).equals(canonical(label))).findFirst().orElse(label);
                if(!text(raw.get(key)).equals(f.get(KEYS.get(i)))) raw.put(key,f.get(KEYS.get(i)));
            }
            meta.put("fields",raw);meta.put("reportCategory",input.category());
            meta.put("currency",text(input.currency()));meta.put("quantityUnit",text(input.quantityUnit()));
            meta.put("priceTerms",text(input.priceTerms()));meta.put("businessStage",text(input.businessStage()));
            try {String json=mapper.writeValueAsString(meta);if(json.length()>64000) throw bad("报告资料过长，请缩短备注");projectInput.setReportData(json);} catch(tools.jackson.core.JacksonException e) {throw new IllegalStateException(e);}
            String mp=f.get("expectedMpText");
            try {LocalDate date=mp.matches("\\d{4}-\\d{2}-\\d{2}")?LocalDate.parse(mp):null;if(date!=null&&date.getYear()<1)throw bad("量产年份须在1到9999之间");projectInput.setExpectedMpDate(date);} catch(Exception e) {throw bad("量产日期格式无效，可填写季度等原精度文字");}
        }
        ProjectRecord saved=workspace.saveProject(id,projectInput);
        if(prepared!=null) d=business.save(saved.getId(),d==null?null:d.id,prepared);
        if(saved.isImportant()!=important) saved=workspace.setImportant(saved.getId(),important);
        return row(saved,d);
    }
    private static ResponseStatusException bad(String message) {return new ResponseStatusException(HttpStatus.BAD_REQUEST,message);}
}
