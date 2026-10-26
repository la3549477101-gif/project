package com.example.odmtracker;

import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.server.ResponseStatusException;

@RestControllerAdvice
public class ApiExceptionHandler {
    @ExceptionHandler(org.springframework.dao.DataIntegrityViolationException.class)
    public ResponseEntity<Map<String,String>> conflict(org.springframework.dao.DataIntegrityViolationException exception) {
        return ResponseEntity.status(409).body(Map.of("message","资料存在冲突，请刷新并核对已有客户后重试"));
    }
    @ExceptionHandler(ResponseStatusException.class)
    public ResponseEntity<Map<String, String>> validation(ResponseStatusException exception) {
        return ResponseEntity.status(exception.getStatusCode()).body(Map.of("message",
            exception.getReason() == null ? "请求失败" : exception.getReason()));
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<Map<String, String>> malformed(HttpMessageNotReadableException exception) {
        return ResponseEntity.badRequest().body(Map.of("message", "数据格式错误，请检查数字、日期及字段类型"));
    }
}
