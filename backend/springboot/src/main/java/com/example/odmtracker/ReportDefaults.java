package com.example.odmtracker;

import jakarta.persistence.*;

@Entity @Table(name="report_entry_defaults")
public class ReportDefaults {
    @Id public Long id=1L;
    @Version public Long revision;
    @Column(length=8000,nullable=false) public String payload;
}
