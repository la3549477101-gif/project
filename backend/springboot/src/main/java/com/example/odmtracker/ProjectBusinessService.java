package com.example.odmtracker;

import java.math.BigDecimal;
import java.time.*;
import java.util.*;
import org.springframework.data.domain.*;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class ProjectBusinessService {
    public static final List<String> STAGES=List.of("报价中","样品送测","NPI（新产品导入）","验证通过待量产","下单量产","验证失败结案","项目取消");
    private final ProjectRepository projects;
    private final ProjectDetailRepository details;
    private final FollowupRepository followups;
    private final WorkspaceService workspace;
    public ProjectBusinessService(ProjectRepository projects,ProjectDetailRepository details,FollowupRepository followups,WorkspaceService workspace) {
        this.projects=projects;this.details=details;this.followups=followups;this.workspace=workspace;
    }
    public ProjectRecord project(Long id) {
        return projects.findById(id).orElseThrow(()->new ResponseStatusException(HttpStatus.NOT_FOUND,"项目不存在"));
    }
    private ProjectRecord lockedProject(Long id) {
        return projects.findLockedById(id).orElseThrow(()->new ResponseStatusException(HttpStatus.NOT_FOUND,"项目不存在"));
    }
    private ProjectDetail detail(Long projectId,Long id) {
        ProjectDetail d=details.findById(id).orElseThrow(()->new ResponseStatusException(HttpStatus.NOT_FOUND,"型号规格明细不存在"));
        if(!Objects.equals(d.projectId,projectId)) throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"型号规格不属于当前项目");
        return d;
    }
    public List<ProjectDetail> list(Long projectId) { project(projectId);return details.findByProjectIdOrderByIdAsc(projectId); }
    private static String text(String raw,int max,String label) {
        String value=raw==null?"":raw.trim();
        if(value.length()>max) throw bad(label+"不能超过"+max+"字");
        return value;
    }
    private static String stage(String value) {
        String result=text(value,255,"业务阶段");
        if(!result.isEmpty()&&!STAGES.contains(result)) throw bad("业务阶段无效，请重新选择");
        return result;
    }
    private static BigDecimal decimal(BigDecimal value,String label) {
        if(value==null) return null;
        BigDecimal result=value.stripTrailingZeros();
        if(value.signum()<0 || result.scale()>6 || (long)result.precision()-result.scale()>13)
            throw bad(label+"必须为非负数，最多13位整数和6位小数");
        return result.signum()==0?BigDecimal.ZERO:result;
    }
    private Object number(BigDecimal value) { return value==null?null:value.stripTrailingZeros().toPlainString(); }
    private Object[] values(ProjectDetail d) { return new Object[]{d.materialModel,d.specification,d.productLine,d.owner,d.businessStage,number(d.quotePrice),d.currency,d.quantityUnit,d.priceTerms,number(d.estimatedAnnualQuantity),number(d.estimatedAnnualRevenue),d.expectedMpText,d.competitor,number(d.competitorPrice),d.statusNote,d.notes,d.reportDate,d.caseStatus,d.reportCategory,d.brand}; }
    private static final String[] LABELS={"材料型号","成品规格","产品线","负责人","业务阶段","当前报价","币种","数量单位","计价与含税说明","预估年用量","预估年营业额","预估量产时间","竞争对手","竞争对手单价","当前业务说明","备注","报告日期","案子状况","报告分类","品牌"};
    private static String display(Object value) { return value==null||value.toString().isEmpty()?"（空）":value.toString(); }
    private String diff(Object[] old,Object[] current) {
        List<String> result=new ArrayList<>();
        for(int i=0;i<LABELS.length;i++) if(!Objects.equals(display(old[i]),display(current[i]))) result.add(LABELS[i]+"："+display(old[i])+" → "+display(current[i]));
        return String.join("；",result);
    }
    private String title(ProjectDetail d) { return (d.materialModel.isEmpty()?"型号待补":d.materialModel)+" / "+(d.specification.isEmpty()?"规格待补":d.specification); }
    private void active(ProjectDetail d) { if(d.archived) throw new ResponseStatusException(HttpStatus.CONFLICT,"该明细已归档，请先恢复后再修改或跟进"); }

    @Transactional
    public ProjectDetail save(Long projectId,Long id,ProjectDetail input) {
        ProjectRecord p=lockedProject(projectId);
        if(input==null) throw bad("明细内容不能为空");
        ProjectDetail d=id==null?new ProjectDetail():detail(projectId,id);
        active(d);
        Object[] old=values(d);
        String model=text(input.materialModel,255,"材料型号"), spec=text(input.specification,255,"成品规格");
        if(model.isEmpty()&&spec.isEmpty()) throw bad("材料型号和成品规格至少填写一项");
        if(details.existsByProjectIdAndMaterialModelIgnoreCaseAndSpecificationIgnoreCaseAndIdNot(projectId,model,spec,id==null?-1L:id))
            throw new ResponseStatusException(HttpStatus.CONFLICT,"该型号和规格已存在（含已归档明细），请编辑或恢复原明细");
        d.projectId=projectId;d.materialModel=model;d.specification=spec;
        d.brand=text(input.brand,255,"品牌");d.productLine=text(input.productLine,255,"产品线");d.owner=text(input.owner,255,"负责人");d.businessStage=stage(input.businessStage);
        d.reportDate=text(input.reportDate,100,"报告日期");d.caseStatus=text(input.caseStatus,255,"案子状况");
        d.reportCategory=text(input.reportCategory,10,"报告分类");
        if(!d.reportCategory.isEmpty()&&!List.of("开发","成交","EOL").contains(d.reportCategory)) throw bad("报告分类无效");
        d.quotePrice=decimal(input.quotePrice,"当前报价");d.currency=text(input.currency,30,"币种");d.quantityUnit=text(input.quantityUnit,30,"数量单位");
        d.priceTerms=text(input.priceTerms,255,"计价与含税说明");d.estimatedAnnualQuantity=decimal(input.estimatedAnnualQuantity,"预估年用量");
        d.estimatedAnnualRevenue=decimal(input.estimatedAnnualRevenue,"预估年营业额");d.expectedMpText=text(input.expectedMpText,100,"预估量产时间");
        d.competitor=text(input.competitor,255,"竞争对手");d.competitorPrice=decimal(input.competitorPrice,"竞争对手单价");
        d.statusNote=text(input.statusNote,2000,"当前业务说明");d.notes=text(input.notes,2000,"备注");
        String difference=diff(old,values(d));
        if(id==null||!difference.isEmpty()) {
            if(id==null) d.createdAt=Instant.now();d.updatedAt=Instant.now(); details.saveAndFlush(d);
            systemHistory(d,id==null?"新增型号规格；"+difference:difference);
            workspace.projectActivity(p,"DETAIL",id==null?"NEW":"UPDATE",title(d),id==null?"新增型号规格；"+difference:difference);
        }
        return d;
    }
    @Transactional
    public ProjectDetail archive(Long projectId,Long id,boolean archived) {
        ProjectRecord p=lockedProject(projectId);ProjectDetail d=detail(projectId,id);
        if(d.archived!=archived) {
            d.archived=archived;d.updatedAt=Instant.now();details.save(d);
            systemHistory(d,archived?"归档明细，保留报价和跟进历史":"恢复明细");
            workspace.projectActivity(p,"DETAIL","UPDATE",title(d),archived?"归档明细，保留报价和跟进历史":"恢复明细");
        }
        return d;
    }
    private void systemHistory(ProjectDetail d,String content) {
        FollowupRecord row=new FollowupRecord();
        row.projectId=d.projectId;row.detailId=d.id;row.materialModel=d.materialModel;row.specification=d.specification;row.businessStage=d.businessStage;
        row.contactDate=LocalDate.now(ZoneOffset.ofHours(8));row.recordedAt=d.updatedAt;
        row.kind="FIELD_CHANGE";row.content=content;row.source="系统字段变更记录（按保存日期）";
        followups.save(row);
    }
    public record FollowupInput(Long detailId,LocalDate contactDate,String content,String source,String nextAction,LocalDate nextContactDate,String newBusinessStage) {}
    @Transactional
    public FollowupRecord append(Long projectId,FollowupInput input) {
        ProjectRecord p=lockedProject(projectId);
        if(input==null||input.contactDate()==null) throw bad("请填写跟进发生日期");
        if(input.contactDate().getYear()<1||input.contactDate().getYear()>9999 || (input.nextContactDate()!=null&&(input.nextContactDate().getYear()<1||input.nextContactDate().getYear()>9999))) throw bad("日期年份须在1到9999之间");
        String content=text(input.content(),4000,"跟进内容"),source=text(input.source(),1000,"资料来源");
        if(content.isEmpty()||source.isEmpty()) throw bad("请填写跟进内容和资料来源");
        String newStage=stage(input.newBusinessStage());
        ProjectDetail d=input.detailId()==null?null:detail(projectId,input.detailId());
        String previousStage=d==null?"":d.businessStage;
        if(d==null&&!newStage.isEmpty()) throw bad("修改业务阶段前请选择具体型号规格");
        String stageChange="";
        if(d!=null) {
            active(d);
            if(!newStage.isEmpty()&&!Objects.equals(newStage,d.businessStage)) {
                stageChange="；业务阶段："+display(d.businessStage)+" → "+newStage;
                d.businessStage=newStage;d.updatedAt=Instant.now();details.save(d);
            }
        }
        FollowupRecord row=new FollowupRecord();
        row.kind="COMMUNICATION";
        row.projectId=projectId;row.detailId=d==null?null:d.id;
        row.materialModel=d==null?"":d.materialModel;row.specification=d==null?"":d.specification;row.businessStage=d==null?"":d.businessStage;
        row.previousBusinessStage=previousStage;
        row.contactDate=input.contactDate();row.content=content;row.source=source;
        row.nextAction=text(input.nextAction(),2000,"下一步计划");row.nextContactDate=input.nextContactDate();row.recordedAt=Instant.now();
        followups.saveAndFlush(row);
        workspace.projectActivity(p,"FOLLOWUP","NEW",d==null?"项目整体跟进":title(d),"跟进日期："+row.contactDate+"；内容："+content+"；来源："+source+stageChange);
        return row;
    }
    public Map<String,Object> history(Long projectId,int page,int size) {
        project(projectId);
        if(page<0||size<1||size>100) throw bad("分页参数无效");
        Page<FollowupRecord> result=followups.findByProjectId(projectId,PageRequest.of(page,size,Sort.by(Sort.Order.desc("contactDate"),Sort.Order.desc("id"))));
        return Map.of("items",result.getContent(),"total",result.getTotalElements(),"page",page,"size",size);
    }
    private static ResponseStatusException bad(String message) {return new ResponseStatusException(HttpStatus.BAD_REQUEST,message);}
}
