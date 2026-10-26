package com.example.odmtracker;
import java.util.List;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.HttpStatus;
@RestController @RequestMapping("/api/customers")
@CrossOrigin(origins={"http://localhost:5173","http://127.0.0.1:5173","${odm.extra-origin:http://127.0.0.1:5173}"})
public class CustomerController {
    private final WorkspaceService workspace; private final CustomerArchiveService archive;
    public CustomerController(WorkspaceService workspace,CustomerArchiveService archive) {this.workspace=workspace;this.archive=archive;}
    @GetMapping public List<CustomerRecord> list(){return workspace.customers();}
    @GetMapping("/{id}") public CustomerRecord get(@PathVariable Long id){return workspace.customer(id);}
    @PostMapping @ResponseStatus(HttpStatus.CREATED)
    public CustomerRecord create(@RequestBody CustomerRecord input){return archive.ensure(workspace.saveCustomer(null,input).id);}
    @PutMapping("/{id}") public CustomerRecord update(@PathVariable Long id,@RequestBody CustomerRecord input){return workspace.saveCustomer(id,input);}
    @PostMapping("/{id}/folder/retry") public CustomerRecord retry(@PathVariable Long id){return archive.ensure(id);}
}
