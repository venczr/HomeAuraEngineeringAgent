using System;

namespace HomeAura.AutoCAD.Agent
{
    internal static class EngineeringNumericGuard
    {
        public static double RequireFinite(
            double value,
            string fieldName)
        {
            if (double.IsNaN(value) ||
                double.IsInfinity(value))
            {
                throw new InvalidOperationException(
                    "Engineering numeric value is not finite: " +
                    fieldName
                );
            }

            return value;
        }

        public static double ReadFiniteSingle(
            byte[] payload,
            string fieldName)
        {
            if (payload == null)
            {
                throw new ArgumentNullException("payload");
            }

            if (payload.Length != 4)
            {
                throw new ArgumentException(
                    "Single-precision payload must contain four bytes.",
                    "payload"
                );
            }

            return RequireFinite(
                BitConverter.ToSingle(payload, 0),
                fieldName
            );
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

            return RequireFinite(midpoint, fieldName);
        }
    }
}
