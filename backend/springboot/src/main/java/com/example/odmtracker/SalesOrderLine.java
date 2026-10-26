package com.example.odmtracker;
import java.math.BigDecimal;
import java.time.LocalDate;
import jakarta.persistence.*;
@Entity @Table(name="sales_order_lines")
public class SalesOrderLine {
    @Id @GeneratedValue(strategy=GenerationType.IDENTITY) public Long id;
    public Long projectId;
    public Long detailId;
    public String projectName;
    public String materialModel;
    public String specification;
    @Column(precision=19,scale=6,nullable=false) public BigDecimal quantity;
    @Column(length=30,nullable=false) public String unit;
    @Column(precision=19,scale=6,nullable=false) public BigDecimal unitPrice;
    @Column(precision=31,scale=2,nullable=false) public BigDecimal amount;
    public LocalDate expectedDeliveryDate;
    @Column(length=1000) public String notes;
}
