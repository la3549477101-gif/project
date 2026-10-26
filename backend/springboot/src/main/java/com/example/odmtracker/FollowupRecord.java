package com.example.odmtracker;
import java.time.*;
import jakarta.persistence.*;
@Entity @Table(name="project_followups", indexes=@Index(name="idx_followup_project", columnList="projectId,contactDate"))
public class FollowupRecord {
    @Id @GeneratedValue(strategy=GenerationType.IDENTITY) public Long id;
    @Column(nullable=false) public Long projectId;
    public Long detailId;
    public String materialModel;
    public String specification;
    public String businessStage;
    public String previousBusinessStage;
    public String kind;
    @Column(nullable=false) public LocalDate contactDate;
    @Lob @Column(nullable=false) public String content;
    @Column(length=1000,nullable=false) public String source;
    @Column(length=2000) public String nextAction;
    public LocalDate nextContactDate;
    public Instant recordedAt;
}
