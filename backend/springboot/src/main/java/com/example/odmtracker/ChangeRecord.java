package com.example.odmtracker;
import java.time.Instant;
import jakarta.persistence.*;
@Entity @Table(name="business_changes", indexes={@Index(name="idx_change_time", columnList="occurredAt")})
public class ChangeRecord {
    @Id @GeneratedValue(strategy=GenerationType.IDENTITY) public Long id;
    public Instant occurredAt;
    public Long customerId;
    public String customerName;
    public Long previousCustomerId;
    public String previousCustomerName;
    public Long projectId;
    @Column(length=2000) public String objectName;
    public String entityType;
    public String action;
    @Lob public String detail;
}
