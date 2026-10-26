package com.example.odmtracker;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
public interface ProjectDetailRepository extends JpaRepository<ProjectDetail,Long> {
    List<ProjectDetail> findByProjectIdOrderByIdAsc(Long projectId);
    boolean existsByProjectIdIn(List<Long> ids);
    boolean existsByProjectIdAndMaterialModelIgnoreCaseAndSpecificationIgnoreCaseAndIdNot(Long projectId,String materialModel,String specification,Long id);
}
