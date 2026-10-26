package com.example.odmtracker;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import jakarta.persistence.LockModeType;
import java.util.Optional;

public interface ProjectRepository extends JpaRepository<ProjectRecord, Long> {
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select p from ProjectRecord p where p.id = :id")
    Optional<ProjectRecord> findLockedById(@Param("id") Long id);
}
