package com.example.odmtracker;

import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.*;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

/** Shared field definitions: API validation, audit labels and frontend form schema. */
public final class CustomerProfile {
    private CustomerProfile() {}
    public record Field(String key, String label, String type, int maxLength,
                        List<String> options, String hint) {}
    public record Group(String key, String title, String hint, List<Field> fields) {}
    private static Field text(String key, String label) { return new Field(key,label,"text",255,List.of(),""); }
    private static Field area(String key, String label, String hint) { return new Field(key,label,"textarea",2000,List.of(),hint); }
    private static Field date(String key, String label) { return new Field(key,label,"date",10,List.of(),""); }
    private static Field select(String key, String label, String... options) { return new Field(key,label,"select",255,List.of(options),""); }

    public static final List<Group> GROUPS=List.of(
        new Group("filing","建档信息","只填写已确认的信息；公司全称仍是唯一必填项。",List.of(
            text("ourCompany","我司交易抬头"), select("filingType","建档类型","新建客户","客户信息变更"),
            text("industry","所属行业"), area("changeContent","变更内容","客户信息变更时按事实填写。"))),
        new Group("contact","联系与需求","原有联系方式保留在基本资料中，不自动拆分或推测。",List.of(
            area("address","联系地址","与注册地址分别核对。"), text("telephone","固定电话"), text("fax","传真"),
            text("email","邮箱"), text("mobile","手机号"), area("demandProducts","需求产品","可填写多项型号或规格。"),
            text("monthlyUsage","客户月用量（含单位）"))),
        new Group("terms","长期交易条件","记录首次约定及正式变更，作为后续订单的默认条件。",List.of(
            area("tradeMethod","交易方式","保留双方约定原意。"),
            select("paymentCondition","收款条件","预付款","货到付款","月结30天","月结60天","月结90天","月结120天","月结150天","月结180天","其他约定"),
            new Field("creditLimit","信用额度（含币种及单位）","text",255,List.of(),"按批准或约定填写；未知留空，不用0代替。"),
            area("extraTerms","其他交易约定","特殊账期或收款安排在此补充，需与收款条件一致。"))),
        new Group("billing","对账与开票","日期可填写每月或相对月份的规则，不强制转换为某个固定日期。",List.of(
            text("reconciliationCycle","对账周期"), text("reconciliationDate","对账日期规则"),
            text("invoiceDate","开票日期规则"), select("taxIncluded","是否含税","是","否"))),
        new Group("documents","资料状态与客户分类","未确认不等于无。客户等级由人工评估后填写。",List.of(
            select("idCopy","法人身份证复印件","有","无"), select("businessLicenseCopy","营业执照复印件","有","无"),
            select("formalContract","是否签订正式合同","是","否"), text("customerGrade","客户等级（人工评估）"),
            select("customerType","客户类型","新开发客户","公司分配客户","其他来源"))),
        new Group("handling","人工经办与审核","仅记录已经实际完成的经办和审核信息；不会自动审批、代签或填入日期。",List.of(
            text("salesperson","业务员"), date("filingDate","经办日期"), text("approver","审批人"),
            date("approvalDate","审批日期"), text("ratifier","核准人"), date("ratificationDate","核准日期")))
    );

    public static List<Field> fields() { return GROUPS.stream().flatMap(g->g.fields().stream()).toList(); }

    /** Omitted profile preserves data; supplied keys merge; explicit blank/null clears a value. */
    public static Map<String,String> merge(Map<String,String> previous, Map<String,String> incoming) {
        Map<String,String> result=new LinkedHashMap<>();
        if(previous!=null) result.putAll(previous);
        if(incoming==null) return result;
        Map<String,Field> definitions=new HashMap<>();
        fields().forEach(f->definitions.put(f.key(),f));
        incoming.forEach((key,raw)->{
            Field field=definitions.get(key);
            if(field==null) throw bad("不支持的客户资料字段："+key);
            String value=raw==null?"":raw.trim();
            if(value.length()>field.maxLength()) throw bad(field.label()+"最多填写"+field.maxLength()+"个字符");
            if(!value.isEmpty() && field.type().equals("select") && !field.options().contains(value))
                throw bad(field.label()+"选项无效，请重新选择");
            if(!value.isEmpty() && field.type().equals("date")) {
                try {
                    if(!value.matches("\\d{4}-\\d{2}-\\d{2}")) throw new DateTimeParseException("format",value,0);
                    LocalDate.parse(value);
                } catch(DateTimeParseException e) { throw bad(field.label()+"应为有效日期（年-月-日）"); }
            }
            if(value.isEmpty()) result.remove(key); else result.put(key,value);
        });
        return result;
    }
    private static ResponseStatusException bad(String message) { return new ResponseStatusException(HttpStatus.BAD_REQUEST,message); }
}
