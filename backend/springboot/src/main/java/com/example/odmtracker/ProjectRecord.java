package com.example.odmtracker;

import java.time.LocalDate;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Lob;

@Entity
@Table(name = "project_records")
public class ProjectRecord {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String terminalCustomer;
    private String odmIntegrator;
    private String moduleFactory;
    private String projectName;
    private String application;
    private String stage;
    private Long testDemandQuantity;
    private Long estimatedTotalDemand;
    private LocalDate expectedMpDate;
    private Boolean important;
    @Lob
    private String reportData;
    public Long customerId;
    @jakarta.persistence.Transient public String customerName;
    public java.time.Instant createdAt;
    public java.time.Instant updatedAt;

    public ProjectRecord() {}
    public boolean isImportant() { return Boolean.TRUE.equals(important); }
    public void setImportant(boolean important) { this.important=important; }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getTerminalCustomer() { return terminalCustomer; }
    public void setTerminalCustomer(String terminalCustomer) { this.terminalCustomer = terminalCustomer; }
    public String getOdmIntegrator() { return odmIntegrator; }
    public void setOdmIntegrator(String odmIntegrator) { this.odmIntegrator = odmIntegrator; }
    public String getModuleFactory() { return moduleFactory; }
    public void setModuleFactory(String moduleFactory) { this.moduleFactory = moduleFactory; }
    public String getProjectName() { return projectName; }
    public void setProjectName(String projectName) { this.projectName = projectName; }
    public String getApplication() { return application; }
    public void setApplication(String application) { this.application = application; }
    public String getStage() { return stage; }
    public void setStage(String stage) { this.stage = stage; }
    public Long getTestDemandQuantity() { return testDemandQuantity; }
    public void setTestDemandQuantity(Long testDemandQuantity) { this.testDemandQuantity = testDemandQuantity; }
    public Long getEstimatedTotalDemand() { return estimatedTotalDemand; }
    public void setEstimatedTotalDemand(Long estimatedTotalDemand) { this.estimatedTotalDemand = estimatedTotalDemand; }
    public LocalDate getExpectedMpDate() { return expectedMpDate; }
    public void setExpectedMpDate(LocalDate expectedMpDate) { this.expectedMpDate = expectedMpDate; }
    public String getReportData() { return reportData; }
    public void setReportData(String reportData) { this.reportData = reportData; }
}
