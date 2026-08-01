using System;

namespace HomeAura.AutoCAD.Agent
{
    internal static class SnapshotNumericGuard
    {
        public static void RequireFinite(
            double value,
            string fieldName)
        {
            if (double.IsNaN(value) ||
                double.IsInfinity(value))
            {
                throw new InvalidOperationException(
                    "Snapshot coordinate is not finite: " +
                    fieldName
                );
            }
        }

        public static double Midpoint(
            double minimum,
            double maximum,
            string fieldName)
        {
            RequireFinite(minimum, fieldName + ".Minimum");
            RequireFinite(maximum, fieldName + ".Maximum");

            double midpoint =
                minimum / 2.0 + maximum / 2.0;

            RequireFinite(midpoint, fieldName);
            return midpoint;
        }
    }
}
