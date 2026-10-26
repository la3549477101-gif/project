package com.example.odmtracker;
import java.time.Instant;
import java.util.Map;
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
    @ElementCollection(fetch=FetchType.EAGER)
    @CollectionTable(name="customer_profile_fields", joinColumns=@JoinColumn(name="customer_id"))
    @MapKeyColumn(name="field_key", length=64)
    @Column(name="field_value", length=2000)
    public Map<String,String> profile;
    @Column(length=2000) public String archivePath;
    public String folderStatus;
    @Column(length=1000) public String folderError;
    public Instant createdAt;
    public Instant updatedAt;
}
