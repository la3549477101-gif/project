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
@CrossOrigin(origins = {"http://localhost:5173", "http://127.0.0.1:5173"})
public class ProjectController {
    private final ProjectRepository repository;

    public ProjectController(ProjectRepository repository) { this.repository = repository; }

    @GetMapping
    public List<ProjectRecord> list(@RequestParam(required = false) String search,
                                    @RequestParam(required = false) String stage) {
        String query = search == null ? "" : search.trim().toLowerCase(Locale.ROOT);
        return repository.findAll().stream()
            .filter(p -> stage == null || stage.isBlank() || stage.equals(p.getStage()))
            .filter(p -> query.isBlank() || contains(p.getTerminalCustomer(), query)
                || contains(p.getOdmIntegrator(), query) || contains(p.getModuleFactory(), query)
                || contains(p.getProjectName(), query) || contains(p.getApplication(), query))
            .toList();
    }

    private boolean contains(String value, String query) {
        return value != null && value.toLowerCase(Locale.ROOT).contains(query);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ProjectRecord create(@RequestBody ProjectRecord project) {
        validate(project);
        project.setId(null);
        return repository.save(project);
    }

    @PutMapping("/{id}")
    public ProjectRecord update(@PathVariable Long id, @RequestBody ProjectRecord input) {
        ProjectRecord current = repository.findById(id)
            .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "项目不存在"));
        validate(input);
        if (input.getReportData() == null) input.setReportData(current.getReportData());
        input.setId(current.getId());
        return repository.save(input);
    }

    @PostMapping("/import")
    @ResponseStatus(HttpStatus.CREATED)
    public List<ProjectRecord> importProjects(@RequestBody List<ProjectRecord> projects) {
        projects.forEach(this::validate);
        projects.forEach(p -> p.setId(null));
        return repository.saveAll(projects);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable Long id) {
        if (!repository.existsById(id)) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "项目不存在");
        repository.deleteById(id);
    }

    @PostMapping("/bulk-delete")
    @Transactional
    public Map<String, Integer> bulkDelete(@RequestBody List<Long> ids) {
        if (ids == null || ids.isEmpty())
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请先选择要删除的项目");
        if (ids.size() > 5000)
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "一次最多删除 5000 个项目");
        if (ids.stream().anyMatch(id -> id == null || id <= 0))
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "项目编号无效，请刷新页面后重试");

        List<Long> uniqueIds = ids.stream().distinct().toList();
        List<ProjectRecord> existing = repository.findAllById(uniqueIds);
        repository.deleteAll(existing);
        return Map.of("deletedCount", existing.size());
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
