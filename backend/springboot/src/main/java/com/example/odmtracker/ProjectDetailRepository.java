package com.example.odmtracker;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
public interface ProjectDetailRepository extends JpaRepository<ProjectDetail,Long> {
    List<ProjectDetail> findByProjectIdOrderByIdAsc(Long projectId);
    boolean existsByProjectIdIn(List<Long> ids);
    @Query("select distinct d.projectId from ProjectDetail d where d.id in :ids")
    List<Long> projectIds(@Param("ids") List<Long> ids);
    boolean existsByProjectIdAndMaterialModelIgnoreCaseAndSpecificationIgnoreCaseAndIdNot(Long projectId,String materialModel,String specification,Long id);
}
