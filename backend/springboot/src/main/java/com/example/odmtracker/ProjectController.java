package com.example.odmtracker;

import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/projects")
@CrossOrigin(origins = {"http://localhost:5173", "http://127.0.0.1:5173","${odm.extra-origin:http://127.0.0.1:5173}"})
public class ProjectController {
    private final WorkspaceService workspace;

    public ProjectController(WorkspaceService workspace) { this.workspace = workspace; }

    @GetMapping
    public List<ProjectRecord> list(@RequestParam(required = false) String search,
                                    @RequestParam(required = false) String stage,
                                    @RequestParam(required = false) Long customerId,
                                    @RequestParam(defaultValue = "false") boolean unassigned) {
        return workspace.list(search,stage,customerId,unassigned);
    }

    private boolean contains(String value, String query) {
        return value != null && value.toLowerCase(Locale.ROOT).contains(query);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ProjectRecord create(@RequestBody ProjectRecord project) {
        validate(project);
        return workspace.saveProject(null, project);
    }

    @PutMapping("/{id}")
    public ProjectRecord update(@PathVariable Long id, @RequestBody ProjectRecord input) {
        validate(input);
        return workspace.saveProject(id, input);
    }

    @PostMapping("/import")
    @ResponseStatus(HttpStatus.CREATED)
    public List<ProjectRecord> importProjects(@RequestBody List<ProjectRecord> projects) {
        if(projects == null || projects.isEmpty() || projects.size()>5000)
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"请选择1到5000条记录");
        projects.forEach(this::validate);
        return workspace.importProjects(projects);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable Long id) {
        workspace.delete(id);
    }

    @PostMapping("/bulk-delete")
    @Transactional
    public Map<String, Integer> bulkDelete(@RequestBody List<Long> ids) {
        return Map.of("deletedCount", workspace.deleteMany(ids));
    }

    public record Assignment(List<Long> ids, Long customerId) {}
    @PostMapping("/assign")
    public Map<String,Integer> assign(@RequestBody Assignment input) {
        return workspace.assign(input.ids(), input.customerId());
    }

    private void validate(ProjectRecord project) {
        if (project == null) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "项目数据不能为空");
        if (project.getReportData() != null && project.getReportData().length() > 64000)
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "开发报告原始资料不能超过 64000 字");
        if (project.getProjectName() == null || project.getProjectName().isBlank())
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "项目名称不能为空");
        if (project.getStage() != null && !project.getStage().isBlank()
                && !List.of("EVT", "DVT", "PVT").contains(project.getStage()))
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "目前阶段只能是 EVT、DVT 或 PVT");
        for (String text : new String[]{project.getTerminalCustomer(), project.getOdmIntegrator(), project.getModuleFactory(), project.getProjectName(), project.getApplication()}) {
            if (text != null && text.length() > 255)
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "文字字段不能超过 255 字");
        }
        if (project.getTestDemandQuantity() != null && (project.getTestDemandQuantity() < 0 || project.getTestDemandQuantity() > 9007199254740991L))
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "测试阶段需求数量必须为 0 到 9007199254740991 之间的整数");
        if (project.getEstimatedTotalDemand() != null && (project.getEstimatedTotalDemand() < 0 || project.getEstimatedTotalDemand() > 9007199254740991L))
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "项目预计总需求量必须为 0 到 9007199254740991 之间的整数");
    }
}
