package com.example.odmtracker;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
public interface CustomerRepository extends JpaRepository<CustomerRecord, Long> {
    Optional<CustomerRecord> findByNormalizedName(String normalizedName);
}
