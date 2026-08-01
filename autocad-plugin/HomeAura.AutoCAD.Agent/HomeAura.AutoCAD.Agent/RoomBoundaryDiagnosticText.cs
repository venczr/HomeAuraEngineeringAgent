using System;
using System.Collections.Generic;
using System.Text;

namespace HomeAura.AutoCAD.Agent
{
    internal static class RoomBoundaryDiagnosticText
    {
        internal const int MaximumDiagnosticLength = 512;
        internal const int MaximumMessages = 8;

        internal static string FormatObservation(
            string handle,
            string objectType,
            string layer,
            string geometrySource,
            IList<string> messages)
        {
            StringBuilder builder = new StringBuilder();
            builder.Append("Handle ");
            builder.Append(
                AutoCadDisplayText.Format(
                    handle,
                    AutoCadDisplayText.IdentifierLimit
                )
            );
            builder.Append(" (");
            builder.Append(
                AutoCadDisplayText.Format(
                    objectType,
                    AutoCadDisplayText.IdentifierLimit
                )
            );
            builder.Append(", слой ");
            builder.Append(
                AutoCadDisplayText.Format(
                    layer,
                    AutoCadDisplayText.NameLimit
                )
            );
            builder.Append(", источник ");
            builder.Append(
                AutoCadDisplayText.Format(
                    geometrySource,
                    AutoCadDisplayText.MessageLimit
                )
            );
            builder.Append(")");

            int messageCount =
                messages == null ? 0 : messages.Count;
            int includedMessageCount = Math.Min(
                messageCount,
                MaximumMessages
            );

            if (includedMessageCount > 0)
            {
                builder.Append(": ");

                for (int index = 0;
                     index < includedMessageCount;
                     index++)
                {
                    if (index > 0)
                    {
                        builder.Append(" ");
                    }

                    builder.Append(
                        AutoCadDisplayText.Format(
                            messages[index],
                            AutoCadDisplayText.MessageLimit
                        )
                    );
                }
            }

            if (messageCount > includedMessageCount)
            {
                builder.Append(" (+");
                builder.Append(
                    messageCount - includedMessageCount
                );
                builder.Append(" сообщений)");
            }

            return AutoCadDisplayText.Format(
                builder.ToString(),
                MaximumDiagnosticLength
            );
        }
    }
}
