package com.example.odmtracker;
import java.time.Instant;
import jakarta.persistence.*;

@Entity
@Table(name="customers")
public class CustomerRecord {
    @Id @GeneratedValue(strategy=GenerationType.IDENTITY) public Long id;
    public String fullName;
    @Column(unique=true, nullable=false) public String normalizedName;
    public String shortName;
    public String contactName;
    public String contactDetails;
    @Column(length=4000) public String notes;
    @Column(length=2000) public String archivePath;
    public String folderStatus;
    @Column(length=1000) public String folderError;
    public Instant createdAt;
    public Instant updatedAt;
}
