package com.example.odmtracker;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import jakarta.persistence.LockModeType;
public interface CustomerRepository extends JpaRepository<CustomerRecord, Long> {
    Optional<CustomerRecord> findByNormalizedName(String normalizedName);
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select c from CustomerRecord c where c.id=:id")
    Optional<CustomerRecord> findLockedById(@Param("id") Long id);
}
