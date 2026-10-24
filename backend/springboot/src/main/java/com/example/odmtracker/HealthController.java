package com.example.odmtracker;

import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {
    private final JdbcTemplate jdbc;

    public HealthController(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    @GetMapping("/api/health")
    public ResponseEntity<Map<String, Object>> health() {
        try {
            boolean writable = Boolean.FALSE.equals(jdbc.queryForObject("CALL READONLY()", Boolean.class));
            return ResponseEntity.status(writable ? 200 : 503).body(Map.of(
                "status", writable ? "ok" : "unavailable",
                "databaseWritable", writable,
                "message", writable ? "数据库可正常读写" : "数据库当前只读，请检查数据目录权限后重新启动应用"));
        } catch (RuntimeException exception) {
            return ResponseEntity.status(503).body(Map.of("status", "unavailable",
                "databaseWritable", false, "message", "无法连接数据库，请检查应用日志"));
        }
    }
}
