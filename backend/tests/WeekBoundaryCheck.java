import java.time.Instant;
import com.example.odmtracker.WeekWindow;
public class WeekBoundaryCheck {
    public static void main(String[] args) {
        check("2026-10-25T15:59:59Z", "2026-10-18T16:00:00Z");
        check("2026-10-25T16:00:00Z", "2026-10-25T16:00:00Z");
        check("2026-10-26T00:00:00Z", "2026-10-25T16:00:00Z");
        check("2026-12-31T20:00:00Z", "2026-12-27T16:00:00Z");
        System.out.println("4 Beijing week-boundary checks passed");
    }
    private static void check(String now,String expected) {
        if(!WeekWindow.start(Instant.parse(now)).equals(Instant.parse(expected)))
            throw new AssertionError(now+" expected "+expected);
    }
}
