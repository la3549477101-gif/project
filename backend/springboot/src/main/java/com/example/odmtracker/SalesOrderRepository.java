package com.example.odmtracker;
import java.math.BigDecimal;
import java.util.*;
import org.springframework.data.domain.*;
import org.springframework.data.jpa.repository.*;
import org.springframework.data.repository.query.Param;
public interface SalesOrderRepository extends JpaRepository<SalesOrder,Long> {
    Optional<SalesOrder> findByRequestKey(String key);
    boolean existsByCustomerIdAndOrderNumberKey(Long customerId,String key);
    @Query("select o from SalesOrder o where (:customerId is null or o.customerId=:customerId)")
    Page<SalesOrder> search(@Param("customerId") Long customerId,Pageable page);
    interface CurrencyTotal {String getCurrency(); BigDecimal getAmount(); Long getOrderCount();}
    @Query("select o.currency as currency,sum(o.totalAmount) as amount,count(o) as orderCount from SalesOrder o where (:customerId is null or o.customerId=:customerId) group by o.currency order by o.currency")
    List<CurrencyTotal> totals(@Param("customerId") Long customerId);
}
