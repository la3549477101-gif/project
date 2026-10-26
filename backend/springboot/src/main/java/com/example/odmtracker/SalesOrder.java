package com.example.odmtracker;
import java.math.BigDecimal;
import java.time.*;
import java.util.*;
import jakarta.persistence.*;

@Entity @Table(name="sales_orders",uniqueConstraints=@UniqueConstraint(name="uk_customer_order_number",columnNames={"customer_id","order_number_key"}))
public class SalesOrder {
    @Id @GeneratedValue(strategy=GenerationType.IDENTITY) public Long id;
    @Column(name="customer_id",nullable=false) public Long customerId;
    @Column(nullable=false) public String customerName;
    @Column(length=100) public String customerOrderNo;
    @Column(name="order_number_key",length=64) public String orderNumberKey;
    @Column(nullable=false,unique=true,length=36) public String requestKey;
    @Column(nullable=false,length=64) public String requestHash;
    @Column(nullable=false) public LocalDate orderDate;
    @Column(nullable=false,length=30) public String purpose;
    @Column(nullable=false,length=3) public String currency;
    @Column(nullable=false,precision=31,scale=2) public BigDecimal totalAmount;
    @Column(nullable=false,length=1000) public String source;
    @Column(length=2000) public String notes;
    public Instant createdAt;
    @Column(nullable=false,length=30) public String taxBasis="INCLUDED";
    @Column(nullable=false,length=30) public String calculationRule="LINE_HALF_UP_2";
    @ElementCollection
    @CollectionTable(name="sales_order_terms",joinColumns=@JoinColumn(name="order_id"))
    @MapKeyColumn(name="field_key",length=64) @Column(name="field_value",length=2000)
    public Map<String,String> termsSnapshot=new LinkedHashMap<>();
    @OneToMany(cascade=CascadeType.ALL) @JoinColumn(name="order_id",nullable=false)
    @OrderColumn(name="line_position")
    public List<SalesOrderLine> lines=new ArrayList<>();
}
