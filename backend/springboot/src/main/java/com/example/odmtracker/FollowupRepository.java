package com.example.odmtracker;
import java.util.List;
import org.springframework.data.domain.*;
import org.springframework.data.jpa.repository.JpaRepository;
public interface FollowupRepository extends JpaRepository<FollowupRecord,Long> {
    Page<FollowupRecord> findByProjectId(Long projectId, Pageable pageable);
    boolean existsByProjectIdIn(List<Long> ids);
}
