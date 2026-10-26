package com.example.odmtracker;

import java.util.*;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.ObjectMapper;

@Service
public class ReportDefaultsService {
    public static final List<String> KEYS=List.of("owner","brand","productLine","currency","quantityUnit","priceTerms");
    private final ReportDefaultsRepository repository;
    private final ObjectMapper mapper;
    public ReportDefaultsService(ReportDefaultsRepository repository,ObjectMapper mapper) {this.repository=repository;this.mapper=mapper;}
    public record Entry(boolean enabled,String value) {}
    public record Config(Long revision,Map<String,Entry> fields) {}
    private Map<String,Entry> empty() {
        Map<String,Entry> fields=new LinkedHashMap<>();KEYS.forEach(k->fields.put(k,new Entry(false,"")));return fields;
    }
    private Config config(ReportDefaults row) {
        if(row==null)return new Config(null,empty());
        try {return new Config(row.revision,mapper.readValue(row.payload,new TypeReference<LinkedHashMap<String,Entry>>(){}));}
        catch(Exception e) {throw new ResponseStatusException(HttpStatus.CONFLICT,"默认填入设置无法读取，请检查后重试，未使用或覆盖损坏设置");}
    }
    @Transactional(readOnly=true)
    public Config read() {return config(repository.findById(1L).orElse(null));}
    @Transactional
    public Config save(Config input) {
        if(input==null||input.fields()==null)throw bad("请填写默认值设置");
        if(!KEYS.containsAll(input.fields().keySet()))throw bad("存在不支持固定填入的字段");
        ReportDefaults row=repository.findById(1L).orElse(null);
        if(!Objects.equals(row==null?null:row.revision,input.revision()))throw new ResponseStatusException(HttpStatus.CONFLICT,"默认设置已被修改，请关闭并重新打开后核对");
        Map<String,Entry> fields=empty();
        input.fields().forEach((key,entry)->{
            if(entry==null)throw bad("默认字段设置不能为空");
            String value=entry.value()==null?"":entry.value().trim();
            int max=List.of("currency","quantityUnit").contains(key)?30:255;
            if(value.length()>max||value.chars().anyMatch(Character::isISOControl))throw bad("默认值过长或包含无效控制字符");
            if(entry.enabled()&&value.isEmpty())throw bad("启用默认填入前请填写内容");
            fields.put(key,new Entry(entry.enabled(),value));
        });
        if(row==null)row=new ReportDefaults();
        row.payload=mapper.writeValueAsString(fields);
        return config(repository.saveAndFlush(row));
    }
    public ReportService.Input apply(ReportService.Input input) {
        if(input==null||input.fields()==null)return input;
        Map<String,Entry> defaults=read().fields();
        Map<String,String> fields=new LinkedHashMap<>(input.fields());
        for(String key:List.of("owner","brand","productLine"))if(!fields.containsKey(key)&&defaults.get(key).enabled())fields.put(key,defaults.get(key).value());
        return new ReportService.Input(input.version(),input.detailId(),input.customerId(),input.important(),input.category(),fields,
            fill(input.currency(),defaults.get("currency")),fill(input.quantityUnit(),defaults.get("quantityUnit")),fill(input.priceTerms(),defaults.get("priceTerms")),input.businessStage());
    }
    private String fill(String explicit,Entry entry) {return explicit==null&&entry.enabled()?entry.value():explicit;}
    private static ResponseStatusException bad(String message) {return new ResponseStatusException(HttpStatus.BAD_REQUEST,message);}
}
