package com.example.odmtracker;
import java.util.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.HttpStatus;
@RestController @RequestMapping("/api/report")
@CrossOrigin(origins={"http://localhost:5173","http://127.0.0.1:5173","${odm.extra-origin:http://127.0.0.1:5173}"})
public class ReportController {
    private final ReportService service;
    private final ReportDefaultsService defaults;
    public ReportController(ReportService service,ReportDefaultsService defaults) {this.service=service;this.defaults=defaults;}
    @GetMapping("/defaults") public ReportDefaultsService.Config defaults() {return defaults.read();}
    @PutMapping("/defaults") public ReportDefaultsService.Config defaults(@RequestBody ReportDefaultsService.Config input) {return defaults.save(input);}
    @GetMapping("/rows") public List<ReportService.Row> rows() {return service.list();}
    @PostMapping("/rows") @ResponseStatus(HttpStatus.CREATED) public ReportService.Row create(@RequestBody ReportService.Input input) {return service.save(null,input);}
    @PutMapping("/rows/{projectId}") public ReportService.Row save(@PathVariable Long projectId,@RequestBody ReportService.Input input) {return service.save(projectId,input);}
}
