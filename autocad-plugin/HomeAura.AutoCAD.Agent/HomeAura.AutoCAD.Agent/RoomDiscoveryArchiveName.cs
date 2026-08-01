using System;
using System.Globalization;

namespace HomeAura.AutoCAD.Agent
{
    internal static class RoomDiscoveryArchiveName
    {
        internal static string Create(
            DateTime generatedAtUtc,
            Guid uniqueId)
        {
            if (generatedAtUtc.Kind != DateTimeKind.Utc)
            {
                throw new ArgumentException(
                    "Generation time must be UTC.",
                    "generatedAtUtc"
                );
            }

            if (uniqueId == Guid.Empty)
            {
                throw new ArgumentException(
                    "A non-empty unique identifier is required.",
                    "uniqueId"
                );
            }

            return
                "room_discovery_" +
                generatedAtUtc.ToString(
                    "yyyyMMddTHHmmss_fffffffZ",
                    CultureInfo.InvariantCulture
                ) +
                "_" + uniqueId.ToString("N") +
                ".json";
        }
    }
}
