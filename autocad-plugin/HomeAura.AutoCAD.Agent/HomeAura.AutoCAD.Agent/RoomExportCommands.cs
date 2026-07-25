using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Text;

using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Geometry;
using Autodesk.AutoCAD.Runtime;

namespace HomeAura.AutoCAD.Agent
{
    public sealed partial class Commands
    {
        [CommandMethod(
            "HA_EXPORT_ROOMS",
            CommandFlags.Modal)]
        public void ExportRooms()
        {
            Document document =
                Application.DocumentManager.MdiActiveDocument;

            if (document == null)
            {
                return;
            }

            Editor editor = document.Editor;

            try
            {
                if (string.IsNullOrWhiteSpace(document.Name) ||
                    !Path.IsPathRooted(document.Name))
                {
                    editor.WriteMessage(
                        "\nСначала сохрани DWG на диск."
                    );

                    return;
                }

                RoomExportReport report =
                    ReadMagiCadRooms(document);

                string drawingDirectory =
                    Path.GetDirectoryName(document.Name);

                if (string.IsNullOrWhiteSpace(
                        drawingDirectory))
                {
                    throw new InvalidOperationException(
                        "Не удалось определить папку DWG."
                    );
                }

                string roomsDirectory =
                    Path.Combine(
                        drawingDirectory,
                        "exports",
                        "rooms"
                    );

                string historyDirectory =
                    Path.Combine(
                        roomsDirectory,
                        "history"
                    );

                Directory.CreateDirectory(roomsDirectory);
                Directory.CreateDirectory(historyDirectory);

                string currentPath =
                    Path.Combine(
                        roomsDirectory,
                        "rooms.json"
                    );

                string timestamp =
                    DateTime.Now.ToString(
                        "yyyyMMdd_HHmmss"
                    );

                string historyPath =
                    Path.Combine(
                        historyDirectory,
                        "rooms_" + timestamp + ".json"
                    );

                WriteRoomsJson(currentPath, report);
                WriteRoomsJson(historyPath, report);

                editor.WriteMessage("\n");
                editor.WriteMessage(
                    "\n===================================="
                );
                editor.WriteMessage(
                    "\n HomeAura — экспорт помещений"
                );
                editor.WriteMessage(
                    "\n===================================="
                );
                editor.WriteMessage(
                    "\nНайдено маркеров: " +
                    report.FoundMarkers
                );
                editor.WriteMessage(
                    "\nЭкспортировано помещений: " +
                    report.Rooms.Count
                );

                int displayCount =
                    Math.Min(report.Rooms.Count, 10);

                for (int index = 0;
                     index < displayCount;
                     index++)
                {
                    MagiCadRoom room =
                        report.Rooms[index];

                    editor.WriteMessage(
                        "\n\n" +
                        room.Code +
                        " — " +
                        room.Name
                    );

                    editor.WriteMessage(
                        "\n  Площадь: " +
                        FormatNumber(room.NetAreaM2) +
                        " м²"
                    );

                    editor.WriteMessage(
                        "\n  Температура: " +
                        FormatNumber(
                            room.HeatingTemperatureC
                        ) +
                        " °C"
                    );

                    editor.WriteMessage(
                        "\n  Приток: " +
                        FormatNumber(
                            room.SupplyAirflowM3H
                        ) +
                        " м³/ч"
                    );

                    editor.WriteMessage(
                        "\n  Вытяжка: " +
                        FormatNumber(
                            room.ExtractAirflowM3H
                        ) +
                        " м³/ч"
                    );

                    editor.WriteMessage(
                        "\n  Теплопотери: " +
                        FormatNumber(
                            room.TotalHeatLossW
                        ) +
                        " Вт"
                    );
                }

                editor.WriteMessage(
                    "\n\nJSON: " + currentPath
                );
                editor.WriteMessage(
                    "\nАрхив: " + historyPath
                );
                editor.WriteMessage(
                    "\n===================================="
                );
                editor.WriteMessage("\n");
            }
            catch (System.Exception exception)
            {
                editor.WriteMessage(
                    "\nОшибка HA_EXPORT_ROOMS: " +
                    exception.Message
                );
            }
        }

        private static RoomExportReport ReadMagiCadRooms(
            Document document)
        {
            RoomExportReport report =
                new RoomExportReport
                {
                    FormatVersion = "1.0",
                    ParserVersion =
                        "MagiCAD-R-2024-UR2-rev1",

                    GeneratedAtUtc =
                        DateTime.UtcNow.ToString("O"),

                    DrawingName =
                        Path.GetFileName(document.Name),

                    DrawingFullPath =
                        document.Name,

                    FoundMarkers = 0,

                    Rooms =
                        new List<MagiCadRoom>(),

                    Warnings =
                        new List<string>()
                };

            Database database =
                document.Database;

            using (Transaction transaction =
                   database.TransactionManager
                       .StartTransaction())
            {
                BlockTable blockTable =
                    transaction.GetObject(
                        database.BlockTableId,
                        OpenMode.ForRead
                    ) as BlockTable;

                if (blockTable == null)
                {
                    throw new InvalidOperationException(
                        "Не удалось открыть таблицу блоков."
                    );
                }

                BlockTableRecord modelSpace =
                    transaction.GetObject(
                        blockTable[
                            BlockTableRecord.ModelSpace
                        ],
                        OpenMode.ForRead
                    ) as BlockTableRecord;

                if (modelSpace == null)
                {
                    throw new InvalidOperationException(
                        "Не удалось открыть пространство модели."
                    );
                }

                foreach (ObjectId objectId
                         in modelSpace)
                {
                    BlockReference marker =
                        transaction.GetObject(
                            objectId,
                            OpenMode.ForRead,
                            false
                        ) as BlockReference;

                    if (marker == null)
                    {
                        continue;
                    }

                    if (!string.Equals(
                            marker.Layer,
                            "MAGIROOMTAG",
                            StringComparison
                                .OrdinalIgnoreCase))
                    {
                        continue;
                    }

                    report.FoundMarkers++;

                    Dictionary<ushort, byte[]>
                        fields =
                            ReadMagiCadFields(
                                transaction,
                                marker
                            );

                    if (fields.Count == 0)
                    {
                        report.Warnings.Add(
                            "Маркер " +
                            marker.Handle +
                            " не содержит MagiCAD-R."
                        );

                        continue;
                    }

                    MagiCadRoom room =
                        ParseRoom(
                            marker,
                            fields
                        );

                    report.Rooms.Add(room);
                }

                transaction.Commit();
            }

            if (report.FoundMarkers == 0)
            {
                report.Warnings.Add(
                    "На слое MAGIROOMTAG " +
                    "не найдено маркеров помещений."
                );
            }

            return report;
        }

        private static Dictionary<ushort, byte[]>
            ReadMagiCadFields(
                Transaction transaction,
                DBObject databaseObject)
        {
            Dictionary<ushort, byte[]> result =
                new Dictionary<ushort, byte[]>();

            if (databaseObject.ExtensionDictionary
                    .IsNull)
            {
                return result;
            }

            DBDictionary extensionDictionary =
                transaction.GetObject(
                    databaseObject.ExtensionDictionary,
                    OpenMode.ForRead
                ) as DBDictionary;

            if (extensionDictionary == null ||
                !extensionDictionary.Contains(
                    "MagiCAD-R"))
            {
                return result;
            }

            ObjectId recordId =
                extensionDictionary.GetAt(
                    "MagiCAD-R"
                );

            Xrecord record =
                transaction.GetObject(
                    recordId,
                    OpenMode.ForRead,
                    false
                ) as Xrecord;

            if (record == null ||
                record.Data == null)
            {
                return result;
            }

            foreach (TypedValue value
                     in record.Data)
            {
                if (value.TypeCode != 310)
                {
                    continue;
                }

                byte[] bytes =
                    value.Value as byte[];

                if (bytes == null ||
                    bytes.Length < 2)
                {
                    continue;
                }

                ushort fieldId =
                    (ushort)(
                        bytes[0] |
                        bytes[1] << 8
                    );

                byte[] payload =
                    new byte[bytes.Length - 2];

                if (payload.Length > 0)
                {
                    Buffer.BlockCopy(
                        bytes,
                        2,
                        payload,
                        0,
                        payload.Length
                    );
                }

                result[fieldId] = payload;
            }

            return result;
        }

        private static MagiCadRoom ParseRoom(
            BlockReference marker,
            Dictionary<ushort, byte[]> fields)
        {
            MagiCadRoom room =
                new MagiCadRoom
                {
                    SourceHandle =
                        marker.Handle.ToString(),

                    SourceLayer =
                        marker.Layer,

                    Position =
                        CreateRoomPoint(
                            marker.Position
                        ),

                    Code =
                        ReadUtf8(
                            fields,
                            0x05DF
                        ),

                    Name =
                        ReadUtf8(
                            fields,
                            0x05E0
                        ),

                    HeatingTemperatureC =
                        ReadSingle(
                            fields,
                            0x05BA
                        ),

                    SupplyAirTemperatureC =
                        ReadSingle(
                            fields,
                            0x05BC
                        ),

                    OutdoorTemperatureC =
    ReadSingle(
        fields,
        0x05BD
    ),

                    RoomHeightMm =
                        ReadSingle(
                            fields,
                            0x0517
                        ),

                    NetAreaM2 =
                        ReadSingle(
                            fields,
                            0x051D
                        ),

                    GrossAreaM2 =
                        ReadSingle(
                            fields,
                            0x051E
                        ),

                    NetVolumeM3 =
                        ReadSingle(
                            fields,
                            0x051F
                        ),

                    GrossVolumeM3 =
                        ReadSingle(
                            fields,
                            0x0520
                        ),

                    SupplyAirflowLs =
                        ReadSingle(
                            fields,
                            0x05B7
                        ),

                    ExtractAirflowLs =
                        ReadSingle(
                            fields,
                            0x05B6
                        ),

                    SupplyAirflowM3H =
                        ReadSingle(
                            fields,
                            0x05D6
                        ),

                    ExtractAirflowM3H =
                        ReadSingle(
                            fields,
                            0x05D7
                        ),

                    SupplyAirflowLsM2 =
                        ReadSingle(
                            fields,
                            0x05D8
                        ),

                    SupplyAirflowM3HM2 =
                        ReadSingle(
                            fields,
                            0x05D9
                        ),

                    AirExchangeRate =
                        ReadSingle(
                            fields,
                            0x05DA
                        ),

                    ExtractPercentOfSupply =
                        ReadSingle(
                            fields,
                            0x05DB
                        ),

                    LeakageFactor =
                        ReadSingle(
                            fields,
                            0x05BE
                        ),

                    TotalHeatLossW =
                        ReadSingle(
                            fields,
                            0x05BF
                        ),

                    HeatLossWM2 =
                        ReadSingle(
                            fields,
                            0x05C9
                        ),

                    SupplyAirHeatLossW =
                        ReadSingle(
                            fields,
                            0x05C6
                        ),

                    ExtractTransferHeatLossW =
                        ReadSingle(
                            fields,
                            0x05C7
                        ),

                    LeakageHeatLossW =
                        ReadSingle(
                            fields,
                            0x05C8
                        ),

                    Warnings =
                        new List<string>()
                };

            if (string.IsNullOrWhiteSpace(
                    room.Code))
            {
                room.Code =
                    marker.Handle.ToString();

                room.Warnings.Add(
                    "Код помещения отсутствует; " +
                    "использован Handle."
                );
            }

            if (string.IsNullOrWhiteSpace(
                    room.Name))
            {
                room.Name =
                    "Без названия";

                room.Warnings.Add(
                    "Название помещения отсутствует."
                );
            }

            if (room.TotalHeatLossW.HasValue)
            {
                double additionalLosses =
                    (room.SupplyAirHeatLossW ?? 0) +
                    (room.ExtractTransferHeatLossW ?? 0) +
                    (room.LeakageHeatLossW ?? 0);

                room.StructuralHeatLossW =
                    room.TotalHeatLossW.Value -
                    additionalLosses;
            }

            return room;
        }

        private static string ReadUtf8(
            Dictionary<ushort, byte[]> fields,
            ushort fieldId)
        {
            byte[] payload;

            if (!fields.TryGetValue(
                    fieldId,
                    out payload) ||
                payload == null ||
                payload.Length == 0)
            {
                return null;
            }

            return Encoding.UTF8
                .GetString(payload)
                .TrimEnd('\0');
        }

        private static double? ReadSingle(
            Dictionary<ushort, byte[]> fields,
            ushort fieldId)
        {
            byte[] payload;

            if (!fields.TryGetValue(
                    fieldId,
                    out payload) ||
                payload == null ||
                payload.Length != 4)
            {
                return null;
            }

            return BitConverter.ToSingle(
                payload,
                0
            );
        }

        private static RoomPoint CreateRoomPoint(
            Point3d point)
        {
            return new RoomPoint
            {
                X = point.X,
                Y = point.Y,
                Z = point.Z
            };
        }

        private static string FormatNumber(
            double? value)
        {
            if (!value.HasValue)
            {
                return "нет данных";
            }

            return value.Value.ToString(
                "0.###",
                System.Globalization
                    .CultureInfo
                    .InvariantCulture
            );
        }

        private static void WriteRoomsJson(
            string path,
            RoomExportReport report)
        {
            DataContractJsonSerializerSettings settings =
                new DataContractJsonSerializerSettings
                {
                    UseSimpleDictionaryFormat = true
                };

            DataContractJsonSerializer serializer =
                new DataContractJsonSerializer(
                    typeof(RoomExportReport),
                    settings
                );

            using (FileStream stream =
                   new FileStream(
                       path,
                       FileMode.Create,
                       FileAccess.Write,
                       FileShare.Read))
            {
                serializer.WriteObject(
                    stream,
                    report
                );
            }
        }
    }

    [DataContract]
    public sealed class RoomExportReport
    {
        [DataMember(Order = 1)]
        public string FormatVersion { get; set; }

        [DataMember(Order = 2)]
        public string ParserVersion { get; set; }

        [DataMember(Order = 3)]
        public string GeneratedAtUtc { get; set; }

        [DataMember(Order = 4)]
        public string DrawingName { get; set; }

        [DataMember(Order = 5)]
        public string DrawingFullPath { get; set; }

        [DataMember(Order = 6)]
        public int FoundMarkers { get; set; }

        [DataMember(Order = 7)]
        public List<MagiCadRoom> Rooms { get; set; }

        [DataMember(Order = 8)]
        public List<string> Warnings { get; set; }
    }

    [DataContract]
    public sealed class MagiCadRoom
    {
        [DataMember(Order = 1)]
        public string SourceHandle { get; set; }

        [DataMember(Order = 2)]
        public string SourceLayer { get; set; }

        [DataMember(Order = 3)]
        public RoomPoint Position { get; set; }

        [DataMember(Order = 4)]
        public string Code { get; set; }

        [DataMember(Order = 5)]
        public string Name { get; set; }

        [DataMember(Order = 6)]
        public double? HeatingTemperatureC { get; set; }

        [DataMember(Order = 7)]
        public double? SupplyAirTemperatureC { get; set; }

        [DataMember(Order = 8)]
        public double? OutdoorTemperatureC { get; set; }

        [DataMember(Order = 9)]
        public double? RoomHeightMm { get; set; }

        [DataMember(Order = 10)]
        public double? NetAreaM2 { get; set; }

        [DataMember(Order = 11)]
        public double? GrossAreaM2 { get; set; }

        [DataMember(Order = 12)]
        public double? NetVolumeM3 { get; set; }

        [DataMember(Order = 13)]
        public double? GrossVolumeM3 { get; set; }

        [DataMember(Order = 14)]
        public double? SupplyAirflowLs { get; set; }

        [DataMember(Order = 15)]
        public double? ExtractAirflowLs { get; set; }

        [DataMember(Order = 16)]
        public double? SupplyAirflowM3H { get; set; }

        [DataMember(Order = 17)]
        public double? ExtractAirflowM3H { get; set; }

        [DataMember(Order = 18)]
        public double? SupplyAirflowLsM2 { get; set; }

        [DataMember(Order = 19)]
        public double? SupplyAirflowM3HM2 { get; set; }

        [DataMember(Order = 20)]
        public double? AirExchangeRate { get; set; }

        [DataMember(Order = 21)]
        public double? ExtractPercentOfSupply { get; set; }

        [DataMember(Order = 22)]
        public double? LeakageFactor { get; set; }

        [DataMember(Order = 23)]
        public double? TotalHeatLossW { get; set; }

        [DataMember(Order = 24)]
        public double? HeatLossWM2 { get; set; }

        [DataMember(Order = 25)]
        public double? StructuralHeatLossW { get; set; }

        [DataMember(Order = 26)]
        public double? SupplyAirHeatLossW { get; set; }

        [DataMember(Order = 27)]
        public double? ExtractTransferHeatLossW { get; set; }

        [DataMember(Order = 28)]
        public double? LeakageHeatLossW { get; set; }

        [DataMember(Order = 29)]
        public List<string> Warnings { get; set; }
    }

    [DataContract]
    public sealed class RoomPoint
    {
        [DataMember(Order = 1)]
        public double X { get; set; }

        [DataMember(Order = 2)]
        public double Y { get; set; }

        [DataMember(Order = 3)]
        public double Z { get; set; }
    }
}