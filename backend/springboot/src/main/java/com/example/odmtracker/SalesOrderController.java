package com.example.odmtracker;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.Map;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
@RestController @RequestMapping("/api/orders")
@CrossOrigin(origins={"http://localhost:5173","http://127.0.0.1:5173","${odm.extra-origin:http://127.0.0.1:5173}"})
public class SalesOrderController {
    private final SalesOrderService service;
    public SalesOrderController(SalesOrderService service){this.service=service;}
    @PostMapping("/preview") public SalesOrderService.OrderView preview(@RequestBody SalesOrderService.OrderInput input){return service.preview(input);}
    @PostMapping @ResponseStatus(HttpStatus.CREATED) public SalesOrderService.OrderView create(@RequestBody SalesOrderService.OrderInput input){return service.create(input);}
    @GetMapping public Map<String,Object> list(@RequestParam(required=false) Long customerId,@RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="20") int size){return service.list(customerId,page,size);}
    @GetMapping("/{id}") public SalesOrderService.OrderView get(@PathVariable Long id){return service.get(id);}
    @GetMapping("/export") public ResponseEntity<byte[]> export(@RequestParam(required=false) Long customerId){
        return ResponseEntity.ok().header(HttpHeaders.CONTENT_DISPOSITION,"attachment; filename=orders-"+LocalDate.now(java.time.ZoneOffset.ofHours(8))+".csv")
            .contentType(new MediaType("text","csv",StandardCharsets.UTF_8)).body(service.export(customerId).getBytes(StandardCharsets.UTF_8));
    }
}
