package com.example.odmtracker;
import java.time.*;
import java.text.Normalizer;
import java.util.*;
import java.util.function.Function;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

@Service
public class WorkspaceService {
    private final ProjectRepository projects;
    private final CustomerRepository customers;
    private final ChangeRepository changes;
    public WorkspaceService(ProjectRepository projects, CustomerRepository customers, ChangeRepository changes) {
        this.projects=projects; this.customers=customers; this.changes=changes;
    }
    public CustomerRecord customer(Long id) {
        return customers.findById(id).orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND,"客户不存在"));
    }
    public List<CustomerRecord> customers() { return customers.findAll(); }
    private String companyName(Long id) { return id==null ? "" : customers.findById(id).map(c->c.fullName).orElse(""); }
    private void checkCustomer(Long id) {
        if (id!=null && (id<=0 || !customers.existsById(id)))
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"所选客户不存在，请重新选择");
    }
    private String text(String value, int max, String label) {
        String s=value==null ? "" : value.trim();
        if(s.length()>max) throw new ResponseStatusException(HttpStatus.BAD_REQUEST,label+"过长");
        return s;
    }
    private String[] customerValues(CustomerRecord c) {
        return new String[]{c.fullName,c.shortName,c.contactName,c.contactDetails,c.notes};
    }
    @Transactional
    public CustomerRecord saveCustomer(Long id, CustomerRecord input) {
        if(input==null) throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"客户资料不能为空");
        String full=text(input.fullName,255,"公司全称").replaceAll("\\s+"," ");
        if(full.isBlank()) throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"公司全称不能为空");
        String normalized=Normalizer.normalize(full,Normalizer.Form.NFKC).toLowerCase(Locale.ROOT);
        customers.findByNormalizedName(normalized).ifPresent(existing->{
            if(!Objects.equals(existing.id,id)) throw new ResponseStatusException(HttpStatus.CONFLICT,"该公司已建档，请选择现有客户");
        });
        CustomerRecord c=id==null ? new CustomerRecord() : customer(id);
        String[] old=customerValues(c);
        c.fullName=full; c.normalizedName=normalized;
        c.shortName=text(input.shortName,255,"简称"); c.contactName=text(input.contactName,255,"联系人");
        c.contactDetails=text(input.contactDetails,255,"联系方式"); c.notes=text(input.notes,4000,"备注");
        String detail=diff(new String[]{"公司全称","简称","联系人","联系方式","备注"}, old, customerValues(c));
        if(id==null) { c.createdAt=Instant.now(); c.folderStatus="PENDING"; }
        if(id==null || !detail.isEmpty()) {
            c.updatedAt=Instant.now(); customers.saveAndFlush(c);
            log(c.id,null,null,c.fullName,"CUSTOMER",id==null?"NEW":"UPDATE",id==null?"建立客户档案":detail);
        }
        return c;
    }
    @Transactional
    public CustomerRecord folderResult(Long id, String path, String error) {
        CustomerRecord c=customer(id);
        if(path!=null && !path.isBlank()) { c.archivePath=path; c.folderStatus="READY"; c.folderError=""; }
        else { c.folderStatus="FAILED"; c.folderError=error==null?"文件夹创建失败":error.substring(0,Math.min(1000,error.length())); }
        return customers.save(c);
    }
    private void log(Long companyId,Long previousId,Long projectId,String name,String type,String action,String detail) {
        ChangeRecord event=new ChangeRecord();
        event.occurredAt=Instant.now(); event.customerId=companyId; event.customerName=companyName(companyId);
        event.previousCustomerId=previousId; event.previousCustomerName=companyName(previousId);
        event.projectId=projectId; event.objectName=name; event.entityType=type; event.action=action; event.detail=detail;
        changes.save(event);
    }
    private static String display(Object value) { return value==null || value.toString().isEmpty() ? "（空）" : value.toString(); }
    private String diff(String[] labels,Object[] before,Object[] after) {
        List<String> result=new ArrayList<>();
        for(int i=0;i<labels.length;i++) if(!Objects.equals(before[i],after[i]))
            result.add(labels[i]+"："+display(before[i])+" → "+display(after[i]));
        return String.join("；",result);
    }
    private String comparable(String value) { return value==null ? "" : value.trim(); }
    private Object[] values(ProjectRecord p) { return new Object[]{p.customerId,comparable(p.getTerminalCustomer()),comparable(p.getOdmIntegrator()),comparable(p.getModuleFactory()),
        comparable(p.getProjectName()),comparable(p.getApplication()),comparable(p.getStage()),p.getTestDemandQuantity(),p.getEstimatedTotalDemand(),p.getExpectedMpDate()}; }
    @Transactional
    public ProjectRecord saveProject(Long id,ProjectRecord input) {
        checkCustomer(input.customerId);
        ProjectRecord p=id==null ? new ProjectRecord() : projects.findById(id)
            .orElseThrow(()->new ResponseStatusException(HttpStatus.NOT_FOUND,"项目不存在"));
        Long oldCompany=p.customerId;
        Object[] old=values(p);
        String oldReport=p.getReportData();
        p.customerId=input.customerId;
        p.setTerminalCustomer(input.getTerminalCustomer()); p.setOdmIntegrator(input.getOdmIntegrator());
        p.setModuleFactory(input.getModuleFactory()); p.setProjectName(input.getProjectName().trim());
        p.setApplication(input.getApplication()); p.setStage(input.getStage()); p.setTestDemandQuantity(input.getTestDemandQuantity());
        p.setEstimatedTotalDemand(input.getEstimatedTotalDemand()); p.setExpectedMpDate(input.getExpectedMpDate());
        if(input.getReportData()!=null) p.setReportData(input.getReportData());
        Object[] after=values(p);
        // Customer names, rather than internal IDs, make ownership changes readable.
        Object[] beforeText=old.clone(), afterText=after.clone();
        beforeText[0]=companyName((Long)old[0]); afterText[0]=companyName(p.customerId);
        String detail=diff(new String[]{"所属公司","终端客户","ODM集成商","模组厂","项目名称","应用","验证阶段","测试需求数量","预计总需求","预计量产日期"},beforeText,afterText);
        if(!Objects.equals(oldReport,p.getReportData())) detail+=(detail.isEmpty()?"":"；")+"原开发报告资料已更新";
        if(id==null) p.createdAt=Instant.now();
        if(id==null || !detail.isEmpty() || !Objects.equals(oldCompany,p.customerId)) {
            p.updatedAt=Instant.now(); projects.saveAndFlush(p);
            log(p.customerId,Objects.equals(oldCompany,p.customerId)?null:oldCompany,p.getId(),p.getProjectName(),"PROJECT",id==null?"NEW":"UPDATE",id==null?"新增项目":detail);
        }
        p.customerName=companyName(p.customerId);
        return p;
    }
    @Transactional
    public List<ProjectRecord> importProjects(List<ProjectRecord> input) {
        input.forEach(p->checkCustomer(p.customerId));
        return input.stream().map(p->saveProject(null,p)).toList();
    }
    @Transactional
    public Map<String,Integer> assign(List<Long> ids,Long customerId) {
        checkCustomer(customerId);
        List<Long> unique=validIds(ids);
        List<ProjectRecord> selected=projects.findAllById(unique);
        if(selected.size()!=unique.size()) throw new ResponseStatusException(HttpStatus.NOT_FOUND,"部分项目已不存在，请刷新后重试");
        int count=0;
        for(ProjectRecord p:selected) if(!Objects.equals(p.customerId,customerId)) {
            Long old=p.customerId;
            p.customerId=customerId; p.updatedAt=Instant.now(); projects.save(p);
            log(customerId,old,p.getId(),p.getProjectName(),"PROJECT","UPDATE","所属公司："+display(companyName(old))+" → "+display(companyName(customerId)));
            count++;
        }
        return Map.of("updatedCount",count);
    }
    static List<Long> validIds(List<Long> ids) {
        if(ids==null || ids.isEmpty() || ids.size()>5000 || ids.stream().anyMatch(id->id==null||id<=0))
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"请选择1到5000个有效项目");
        return ids.stream().distinct().toList();
    }
    @Transactional
    public int deleteMany(List<Long> ids) {
        List<ProjectRecord> selected=projects.findAllById(validIds(ids));
        projects.deleteAll(selected); return selected.size();
    }
    @Transactional
    public void delete(Long id) {
        ProjectRecord p=projects.findById(id).orElseThrow(()->new ResponseStatusException(HttpStatus.NOT_FOUND,"项目不存在"));
        projects.delete(p);
    }
    public List<ProjectRecord> list(String search,String stage,Long customerId,boolean unassigned) {
        if(customerId!=null) checkCustomer(customerId);
        String query=search==null?"":search.trim().toLowerCase(Locale.ROOT);
        Map<Long,String> names=new HashMap<>(); customers.findAll().forEach(c->names.put(c.id,c.fullName));
        return projects.findAll().stream().filter(p->customerId==null||Objects.equals(p.customerId,customerId))
            .filter(p->!unassigned||p.customerId==null)
            .filter(p->stage==null||stage.isBlank()||stage.equals(p.getStage()))
            .peek(p->p.customerName=p.customerId==null?"":names.getOrDefault(p.customerId,""))
            .filter(p->query.isBlank()||Arrays.asList(p.customerName,p.getTerminalCustomer(),p.getOdmIntegrator(),p.getModuleFactory(),p.getProjectName(),p.getApplication())
                .stream().anyMatch(v->v!=null&&v.toLowerCase(Locale.ROOT).contains(query))).toList();
    }
}
