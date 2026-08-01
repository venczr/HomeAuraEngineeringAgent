using System;

namespace HomeAura.AutoCAD.Agent
{
    internal enum AutoCadCommandOperation
    {
        AnalyzeModel,
        FindRemoteObject,
        ExportModel,
        DiscoverRoom,
        DiscoverRoomBoundaries,
        ExportRooms,
        SyncModel,
        SyncRooms
    }

    internal static class AutoCadCommandDiagnostics
    {
        internal static string FormatUnexpected(
            AutoCadCommandOperation operation)
        {
            string commandName;

            switch (operation)
            {
                case AutoCadCommandOperation.AnalyzeModel:
                    commandName = "HA_ANALYZE_MODEL";
                    break;
                case AutoCadCommandOperation.FindRemoteObject:
                    commandName = "HA_FIND_REMOTE_OBJECT";
                    break;
                case AutoCadCommandOperation.ExportModel:
                    commandName = "HA_EXPORT_MODEL";
                    break;
                case AutoCadCommandOperation.DiscoverRoom:
                    commandName = "HA_DISCOVER_ROOM";
                    break;
                case AutoCadCommandOperation.DiscoverRoomBoundaries:
                    commandName = "HA_DISCOVER_ROOM_BOUNDARIES";
                    break;
                case AutoCadCommandOperation.ExportRooms:
                    commandName = "HA_EXPORT_ROOMS";
                    break;
                case AutoCadCommandOperation.SyncModel:
                    commandName = "HA_SYNC_MODEL";
                    break;
                case AutoCadCommandOperation.SyncRooms:
                    commandName = "HA_SYNC_ROOMS";
                    break;
                default:
                    throw new ArgumentOutOfRangeException(
                        nameof(operation),
                        operation,
                        "Unknown AutoCAD command operation."
                    );
            }

            return
                "\nКоманда " + commandName +
                " завершилась с внутренней ошибкой. " +
                "Подробности скрыты. Повторите команду; " +
                "если ошибка сохраняется, зафиксируйте имя " +
                "команды и состояние чертежа.";
        }

        internal static string FormatBoundaryMeasurementFailure()
        {
            return
                "AutoCAD не вычислил точную площадь/длину; " +
                "контур исключён из валидных границ.";
        }
    }

    internal sealed class AutoCadCommandUserException : Exception
    {
        internal const int MaximumMessageLength = 256;

        internal AutoCadCommandUserException(string safeMessage)
            : base(Validate(safeMessage))
        {
            SafeMessage = safeMessage;
        }

        internal string SafeMessage { get; private set; }

        private static string Validate(string safeMessage)
        {
            if (string.IsNullOrWhiteSpace(safeMessage))
            {
                throw new ArgumentException(
                    "A safe user message is required.",
                    nameof(safeMessage)
                );
            }

            if (safeMessage.Length > MaximumMessageLength)
            {
                throw new ArgumentOutOfRangeException(
                    nameof(safeMessage),
                    safeMessage.Length,
                    "The safe user message is too long."
                );
            }

            if (safeMessage.IndexOf('\r') >= 0 ||
                safeMessage.IndexOf('\n') >= 0)
            {
                throw new ArgumentException(
                    "A safe user message must be one line.",
                    nameof(safeMessage)
                );
            }

            return safeMessage;
        }
    }
}
