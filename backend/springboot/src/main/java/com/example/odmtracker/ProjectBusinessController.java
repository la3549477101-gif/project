package com.example.odmtracker;
import java.util.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
@RestController @RequestMapping("/api/projects")
@CrossOrigin(origins={"http://localhost:5173","http://127.0.0.1:5173","${odm.extra-origin:http://127.0.0.1:5173}"})
public class ProjectBusinessController {
    private final ProjectBusinessService service;
    public ProjectBusinessController(ProjectBusinessService service) {this.service=service;}
    @GetMapping("/detail-options") public Map<String,Object> options() {return Map.of("businessStages",ProjectBusinessService.STAGES);}
    @GetMapping("/{projectId}/details") public List<ProjectDetail> list(@PathVariable Long projectId) {return service.list(projectId);}
    @PostMapping("/{projectId}/details") @ResponseStatus(HttpStatus.CREATED)
    public ProjectDetail create(@PathVariable Long projectId,@RequestBody ProjectDetail input) {return service.save(projectId,null,input);}
    @PutMapping("/{projectId}/details/{id}")
    public ProjectDetail update(@PathVariable Long projectId,@PathVariable Long id,@RequestBody ProjectDetail input) {return service.save(projectId,id,input);}
    public record ArchiveInput(Boolean archived) {}
    @PostMapping("/{projectId}/details/{id}/archive")
    public ProjectDetail archive(@PathVariable Long projectId,@PathVariable Long id,@RequestBody ArchiveInput input) {
        if(input==null||input.archived()==null) throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"请指定归档或恢复操作");
        return service.archive(projectId,id,input.archived());
    }
    @GetMapping("/{projectId}/followups") public Map<String,Object> history(@PathVariable Long projectId,@RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="20") int size) {return service.history(projectId,page,size);}
    @PostMapping("/{projectId}/followups") @ResponseStatus(HttpStatus.CREATED)
    public FollowupRecord append(@PathVariable Long projectId,@RequestBody ProjectBusinessService.FollowupInput input) {return service.append(projectId,input);}
}
