package com.example.odmtracker;
import java.time.*;
import java.time.temporal.TemporalAdjusters;
import java.util.Map;
import org.springframework.data.domain.*;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
@RestController @RequestMapping("/api/activities")
@CrossOrigin(origins={"http://localhost:5173","http://127.0.0.1:5173","${odm.extra-origin:http://127.0.0.1:5173}"})
public class ActivityController {
    private final ChangeRepository changes;
    public ActivityController(ChangeRepository changes){this.changes=changes;}
    public static Instant weekStart(Instant now) {
        return WeekWindow.start(now);
    }
    @GetMapping public Map<String,Object> list(@RequestParam(defaultValue="week") String scope,
        @RequestParam(required=false) Long customerId,@RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="25") int size) {
        if(!scope.equals("week")&&!scope.equals("all")||page<0||size<1||size>100||customerId!=null&&customerId<=0)
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"更新记录查询参数无效");
        Instant from=scope.equals("week")?weekStart(Instant.now()):Instant.EPOCH;
        Instant to=scope.equals("week")?from.plus(Duration.ofDays(7)):Instant.parse("3000-01-01T00:00:00Z");
        Page<ChangeRecord> results=changes.search(from,to,customerId,PageRequest.of(page,size,Sort.by(Sort.Direction.DESC,"occurredAt","id")));
        return Map.of("items",results.getContent(),"total",results.getTotalElements(),"page",page,"size",size,"from",from,"to",to,"timezone","Asia/Shanghai");
    }
}
