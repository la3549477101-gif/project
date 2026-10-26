package com.example.odmtracker;

import java.math.BigDecimal;
import java.time.Instant;
import jakarta.persistence.*;
import com.fasterxml.jackson.annotation.JsonFormat;

@Entity @Table(name="project_details", indexes=@Index(name="idx_detail_project", columnList="projectId"))
public class ProjectDetail {
    @Id @GeneratedValue(strategy=GenerationType.IDENTITY) public Long id;
    @Column(nullable=false) public Long projectId;
    public String materialModel;
    public String specification;
    public String productLine;
    public String owner;
    public String reportDate;
    public String caseStatus;
    public String reportCategory;
    public String businessStage;
    @Column(precision=19,scale=6) @JsonFormat(shape=JsonFormat.Shape.STRING) public BigDecimal quotePrice;
    public String currency;
    public String quantityUnit;
    public String priceTerms;
    @Column(precision=19,scale=6) @JsonFormat(shape=JsonFormat.Shape.STRING) public BigDecimal estimatedAnnualQuantity;
    @Column(precision=19,scale=6) @JsonFormat(shape=JsonFormat.Shape.STRING) public BigDecimal estimatedAnnualRevenue;
    public String expectedMpText;
    public String competitor;
    @Column(precision=19,scale=6) @JsonFormat(shape=JsonFormat.Shape.STRING) public BigDecimal competitorPrice;
    @Column(length=2000) public String statusNote;
    @Column(length=2000) public String notes;
    public boolean archived;
    public Instant createdAt;
    public Instant updatedAt;
}
