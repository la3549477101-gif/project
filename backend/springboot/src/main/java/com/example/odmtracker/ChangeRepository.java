package com.example.odmtracker;
import java.time.Instant;
import org.springframework.data.domain.*;
import org.springframework.data.jpa.repository.*;
import org.springframework.data.repository.query.Param;
public interface ChangeRepository extends JpaRepository<ChangeRecord, Long> {
    @Query("select a from ChangeRecord a where a.occurredAt >= :fromTime and a.occurredAt < :toTime and (:customerId is null or a.customerId = :customerId or a.previousCustomerId = :customerId)")
    Page<ChangeRecord> search(@Param("fromTime") Instant fromTime, @Param("toTime") Instant toTime,
        @Param("customerId") Long customerId, Pageable pageable);
}
