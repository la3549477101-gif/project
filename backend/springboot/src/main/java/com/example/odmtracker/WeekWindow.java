package com.example.odmtracker;
import java.time.*;
import java.time.temporal.TemporalAdjusters;
/** Calendar boundaries are independent of the host computer's time zone. */
public final class WeekWindow {
    private WeekWindow() {}
    public static Instant start(Instant now) {
        return now.atOffset(ZoneOffset.ofHours(8)).toLocalDate()
            .with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY))
            .atStartOfDay().toInstant(ZoneOffset.ofHours(8));
    }
}
