using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;

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
            "HA_DISCOVER_ROOM",
            CommandFlags.Modal | CommandFlags.UsePickSet)]
        public void DiscoverRoom()
        {
            Document document =
                Application.DocumentManager.MdiActiveDocument;

            if (document == null)
            {
                return;
            }

            Editor editor = document.Editor;

            if (string.IsNullOrWhiteSpace(document.Name) ||
                !Path.IsPathRooted(document.Name))
            {
                editor.WriteMessage(
                    "\nСначала сохрани DWG на диск."
                );

                return;
            }

            PromptSelectionOptions options =
                new PromptSelectionOptions
                {
                    MessageForAdding =
                        "\nВыбери маркер помещения, " +
                        "контур и связанные объекты, " +
                        "затем нажми Enter: "
                };

            PromptSelectionResult result =
                editor.GetSelection(options);

            if (result.Status != PromptStatus.OK)
            {
                editor.WriteMessage(
                    "\nВыбор объектов отменён."
                );

                return;
            }

            try
            {
                RoomDiscoveryReport report =
                    new RoomDiscoveryReport
                    {
                        GeneratedAtUtc =
                            DateTime.UtcNow.ToString("O"),

                        DrawingName =
                            Path.GetFileName(document.Name),

                        DrawingFullPath =
                            document.Name,

                        Objects =
                            new List<DiscoveredObject>()
                    };

                using (Transaction transaction =
                       document.Database
                           .TransactionManager
                           .StartTransaction())
                {
                    foreach (ObjectId objectId
                             in result.Value.GetObjectIds())
                    {
                        DBObject databaseObject =
                            transaction.GetObject(
                                objectId,
                                OpenMode.ForRead,
                                false
                            );

                        if (databaseObject == null)
                        {
                            continue;
                        }

                        DiscoveredObject discovered =
                            InspectObject(
                                transaction,
                                databaseObject
                            );

                        report.Objects.Add(discovered);
                    }

                    transaction.Commit();
                }

                string drawingDirectory =
                    Path.GetDirectoryName(document.Name);

                if (string.IsNullOrWhiteSpace(
                        drawingDirectory))
                {
                    throw new InvalidOperationException(
                        "Не определена папка DWG."
                    );
                }

                string exportDirectory =
                    Path.Combine(
                        drawingDirectory,
                        "exports",
                        "discovery"
                    );

                string fileName =
                    "room_discovery_" +
                    DateTime.Now.ToString(
                        "yyyyMMdd_HHmmss"
                    ) +
                    ".json";

                string exportPath =
                    Path.Combine(
                        exportDirectory,
                        fileName
                    );

                WriteDiscoveryJson(
                    drawingDirectory,
                    exportPath,
                    report
                );

                editor.WriteMessage("\n");
                editor.WriteMessage(
                    "\n===================================="
                );
                editor.WriteMessage(
                    "\n HomeAura — обнаружение данных Room"
                );
                editor.WriteMessage(
                    "\n===================================="
                );
                editor.WriteMessage(
                    "\nВыбрано объектов: " +
                    report.Objects.Count
                );

                int displayCount =
                    Math.Min(report.Objects.Count, 15);

                for (int index = 0;
                     index < displayCount;
                     index++)
                {
                    DiscoveredObject item =
                        report.Objects[index];

                    editor.WriteMessage(
                        "\n" +
                        item.Handle +
                        " | " +
                        item.DxfName +
                        " | " +
                        item.DotNetType
                    );

                    if (!string.IsNullOrWhiteSpace(
                            item.Text))
                    {
                        editor.WriteMessage(
                            "\n  Текст: " + item.Text
                        );
                    }

                    if (!string.IsNullOrWhiteSpace(
                            item.BlockName))
                    {
                        editor.WriteMessage(
                            "\n  Блок: " + item.BlockName
                        );
                    }
                }

                editor.WriteMessage(
                    "\n\nJSON: " + exportPath
                );
                editor.WriteMessage(
                    "\n===================================="
                );
                editor.WriteMessage("\n");
            }
            catch (System.Exception)
            {
                editor.WriteMessage(
                    AutoCadCommandDiagnostics.FormatUnexpected(
                        AutoCadCommandOperation.DiscoverRoom
                    )
                );
            }
        }

        private static DiscoveredObject InspectObject(
            Transaction transaction,
            DBObject databaseObject)
        {
            RXClass rxClass =
                databaseObject.GetRXClass();

            DiscoveredObject result =
                new DiscoveredObject
                {
                    Handle =
                        databaseObject.Handle.ToString(),

                    DxfName =
                        rxClass == null
                            ? "UNKNOWN"
                            : rxClass.DxfName,

                    RxClassName =
                        rxClass == null
                            ? "UNKNOWN"
                            : rxClass.Name,

                    DotNetType =
                        databaseObject.GetType().FullName ??
                        databaseObject.GetType().Name,

                    Attributes =
                        new List<NameValueItem>(),

                    DynamicProperties =
                        new List<NameValueItem>(),

                    PublicProperties =
                        new List<NameValueItem>(),

                    XData =
                        new List<TypedValueItem>(),

                    ExtensionDictionary =
                        new List<DictionaryDataItem>()
                };

            Entity entity =
                databaseObject as Entity;

            if (entity != null)
            {
                result.Layer = entity.Layer;

                try
                {
                    Extents3d extents =
                        entity.GeometricExtents;

                    EngineeringNumericGuard.RequireFinite(
                        extents.MinPoint.X,
                        "RoomDiscovery.Extents.MinimumX"
                    );
                    EngineeringNumericGuard.RequireFinite(
                        extents.MinPoint.Y,
                        "RoomDiscovery.Extents.MinimumY"
                    );
                    EngineeringNumericGuard.RequireFinite(
                        extents.MinPoint.Z,
                        "RoomDiscovery.Extents.MinimumZ"
                    );
                    EngineeringNumericGuard.RequireFinite(
                        extents.MaxPoint.X,
                        "RoomDiscovery.Extents.MaximumX"
                    );
                    EngineeringNumericGuard.RequireFinite(
                        extents.MaxPoint.Y,
                        "RoomDiscovery.Extents.MaximumY"
                    );
                    EngineeringNumericGuard.RequireFinite(
                        extents.MaxPoint.Z,
                        "RoomDiscovery.Extents.MaximumZ"
                    );

                    result.Extents =
                        new ObjectExtents
                        {
                            MinimumX =
                                extents.MinPoint.X,
                            MinimumY =
                                extents.MinPoint.Y,
                            MinimumZ =
                                extents.MinPoint.Z,
                            MaximumX =
                                extents.MaxPoint.X,
                            MaximumY =
                                extents.MaxPoint.Y,
                            MaximumZ =
                                extents.MaxPoint.Z
                        };
                }
                catch
                {
                    // Некоторые объекты не имеют
                    // доступных геометрических границ.
                }
            }

            DBText dbText =
                databaseObject as DBText;

            if (dbText != null)
            {
                result.Text = dbText.TextString;
            }

            MText mText =
                databaseObject as MText;

            if (mText != null)
            {
                result.Text = mText.Text;
            }

            BlockReference blockReference =
                databaseObject as BlockReference;

            if (blockReference != null)
            {
                ObjectId blockDefinitionId =
                    blockReference.IsDynamicBlock
                        ? blockReference
                            .DynamicBlockTableRecord
                        : blockReference.BlockTableRecord;

                if (!blockDefinitionId.IsNull)
                {
                    BlockTableRecord blockDefinition =
                        transaction.GetObject(
                            blockDefinitionId,
                            OpenMode.ForRead
                        ) as BlockTableRecord;

                    if (blockDefinition != null)
                    {
                        result.BlockName =
                            blockDefinition.Name;
                    }
                }

                foreach (ObjectId attributeId
                         in blockReference
                             .AttributeCollection)
                {
                    AttributeReference attribute =
                        transaction.GetObject(
                            attributeId,
                            OpenMode.ForRead
                        ) as AttributeReference;

                    if (attribute == null)
                    {
                        continue;
                    }

                    result.Attributes.Add(
                        new NameValueItem
                        {
                            Name = attribute.Tag,
                            Value =
                                attribute.TextString
                        }
                    );
                }

                if (blockReference.IsDynamicBlock)
                {
                    foreach (
                        DynamicBlockReferenceProperty
                        property
                        in blockReference
                            .DynamicBlockReferencePropertyCollection)
                    {
                        result.DynamicProperties.Add(
                            new NameValueItem
                            {
                                Name =
                                    property.PropertyName,

                                Value =
                                    FormatValue(
                                        property.Value
                                    )
                            }
                        );
                    }
                }
            }

            ReadPublicProperties(
                databaseObject,
                result.PublicProperties
            );

            ReadXData(
                databaseObject,
                result.XData
            );

            if (!databaseObject.ExtensionDictionary
                    .IsNull)
            {
                ReadExtensionDictionary(
                    transaction,
                    databaseObject
                        .ExtensionDictionary,
                    string.Empty,
                    result.ExtensionDictionary,
                    0
                );
            }

            return result;
        }

        private static void ReadPublicProperties(
            object source,
            List<NameValueItem> target)
        {
            PropertyInfo[] properties =
                source.GetType().GetProperties(
                    BindingFlags.Instance |
                    BindingFlags.Public
                );

            foreach (PropertyInfo property
                     in properties)
            {
                if (!property.CanRead ||
                    property.GetIndexParameters()
                        .Length != 0)
                {
                    continue;
                }

                try
                {
                    object value =
                        property.GetValue(
                            source,
                            null
                        );

                    string formatted =
                        FormatSimpleValue(value);

                    if (formatted == null)
                    {
                        continue;
                    }

                    target.Add(
                        new NameValueItem
                        {
                            Name = property.Name,
                            Value = formatted
                        }
                    );
                }
                catch
                {
                    // Некоторые свойства AutoCAD
                    // недоступны в текущем состоянии.
                }
            }
        }

        private static string FormatSimpleValue(
            object value)
        {
            if (value == null)
            {
                return null;
            }

            Type valueType = value.GetType();

            if (valueType.IsPrimitive ||
                value is string ||
                value is decimal ||
                value is DateTime ||
                value is Guid ||
                valueType.IsEnum ||
                value is ObjectId ||
                value is Handle ||
                value is Point2d ||
                value is Point3d ||
                value is Vector2d ||
                value is Vector3d)
            {
                return FormatValue(value);
            }

            return null;
        }

        private static string FormatValue(
    object value)
        {
            if (value == null)
            {
                return string.Empty;
            }

            byte[] byteArray = value as byte[];

            if (byteArray != null)
            {
                return
                    "BASE64:" +
                    Convert.ToBase64String(byteArray);
            }

            IFormattable formattable =
                value as IFormattable;

            if (formattable != null)
            {
                return formattable.ToString(
                    null,
                    CultureInfo.InvariantCulture
                );
            }

            return Convert.ToString(
                value,
                CultureInfo.InvariantCulture
            );
        }

        private static void ReadXData(
            DBObject databaseObject,
            List<TypedValueItem> target)
        {
            ResultBuffer buffer =
                databaseObject.XData;

            if (buffer == null)
            {
                return;
            }

            foreach (TypedValue typedValue
                     in buffer)
            {
                target.Add(
                    new TypedValueItem
                    {
                        TypeCode =
                            typedValue.TypeCode,

                        Value =
                            FormatValue(
                                typedValue.Value
                            )
                    }
                );
            }
        }

        private static void ReadExtensionDictionary(
            Transaction transaction,
            ObjectId dictionaryId,
            string parentPath,
            List<DictionaryDataItem> target,
            int depth)
        {
            if (depth > 8)
            {
                return;
            }

            DBDictionary dictionary =
                transaction.GetObject(
                    dictionaryId,
                    OpenMode.ForRead
                ) as DBDictionary;

            if (dictionary == null)
            {
                return;
            }

            foreach (DBDictionaryEntry entry
                     in dictionary)
            {
                DBObject child =
                    transaction.GetObject(
                        entry.Value,
                        OpenMode.ForRead,
                        false
                    );

                if (child == null)
                {
                    continue;
                }

                string currentPath =
                    string.IsNullOrWhiteSpace(
                        parentPath)
                        ? entry.Key
                        : parentPath + "/" + entry.Key;

                Xrecord xrecord =
                    child as Xrecord;

                if (xrecord != null)
                {
                    DictionaryDataItem item =
                        new DictionaryDataItem
                        {
                            Path = currentPath,
                            ObjectType =
                                child.GetType()
                                    .FullName,
                            Values =
                                new List<TypedValueItem>()
                        };

                    ResultBuffer data =
                        xrecord.Data;

                    if (data != null)
                    {
                        foreach (TypedValue value
                                 in data)
                        {
                            item.Values.Add(
                                new TypedValueItem
                                {
                                    TypeCode =
                                        value.TypeCode,

                                    Value =
                                        FormatValue(
                                            value.Value
                                        )
                                }
                            );
                        }
                    }

                    target.Add(item);
                    continue;
                }

                DBDictionary nestedDictionary =
                    child as DBDictionary;

                if (nestedDictionary != null)
                {
                    ReadExtensionDictionary(
                        transaction,
                        entry.Value,
                        currentPath,
                        target,
                        depth + 1
                    );

                    continue;
                }

                target.Add(
                    new DictionaryDataItem
                    {
                        Path = currentPath,
                        ObjectType =
                            child.GetType().FullName,
                        Values =
                            new List<TypedValueItem>()
                    }
                );
            }
        }

        private static void WriteDiscoveryJson(
            string trustedRoot,
            string path,
            RoomDiscoveryReport report)
        {
            DataContractJsonSerializerSettings settings =
                new DataContractJsonSerializerSettings
                {
                    UseSimpleDictionaryFormat = true
                };

            DataContractJsonSerializer serializer =
                new DataContractJsonSerializer(
                    typeof(RoomDiscoveryReport),
                    settings
                );

            AtomicFileWriter.Write(
                trustedRoot,
                path,
                delegate(Stream stream)
                {
                    serializer.WriteObject(
                        stream,
                        report
                    );
                }
            );
        }
    }

    [DataContract]
    public sealed class RoomDiscoveryReport
    {
        [DataMember(Order = 1)]
        public string GeneratedAtUtc { get; set; }

        [DataMember(Order = 2)]
        public string DrawingName { get; set; }

        [DataMember(Order = 3)]
        public string DrawingFullPath { get; set; }

        [DataMember(Order = 4)]
        public List<DiscoveredObject> Objects { get; set; }
    }

    [DataContract]
    public sealed class DiscoveredObject
    {
        [DataMember(Order = 1)]
        public string Handle { get; set; }

        [DataMember(Order = 2)]
        public string DxfName { get; set; }

        [DataMember(Order = 3)]
        public string RxClassName { get; set; }

        [DataMember(Order = 4)]
        public string DotNetType { get; set; }

        [DataMember(Order = 5)]
        public string Layer { get; set; }

        [DataMember(Order = 6)]
        public string Text { get; set; }

        [DataMember(Order = 7)]
        public string BlockName { get; set; }

        [DataMember(Order = 8)]
        public ObjectExtents Extents { get; set; }

        [DataMember(Order = 9)]
        public List<NameValueItem> Attributes { get; set; }

        [DataMember(Order = 10)]
        public List<NameValueItem> DynamicProperties { get; set; }

        [DataMember(Order = 11)]
        public List<NameValueItem> PublicProperties { get; set; }

        [DataMember(Order = 12)]
        public List<TypedValueItem> XData { get; set; }

        [DataMember(Order = 13)]
        public List<DictionaryDataItem> ExtensionDictionary { get; set; }
    }

    [DataContract]
    public sealed class NameValueItem
    {
        [DataMember(Order = 1)]
        public string Name { get; set; }

        [DataMember(Order = 2)]
        public string Value { get; set; }
    }

    [DataContract]
    public sealed class TypedValueItem
    {
        [DataMember(Order = 1)]
        public int TypeCode { get; set; }

        [DataMember(Order = 2)]
        public string Value { get; set; }
    }

    [DataContract]
    public sealed class DictionaryDataItem
    {
        [DataMember(Order = 1)]
        public string Path { get; set; }

        [DataMember(Order = 2)]
        public string ObjectType { get; set; }

        [DataMember(Order = 3)]
        public List<TypedValueItem> Values { get; set; }
    }

    [DataContract]
    public sealed class ObjectExtents
    {
        [DataMember(Order = 1)]
        public double MinimumX { get; set; }

        [DataMember(Order = 2)]
        public double MinimumY { get; set; }

        [DataMember(Order = 3)]
        public double MinimumZ { get; set; }

        [DataMember(Order = 4)]
        public double MaximumX { get; set; }

        [DataMember(Order = 5)]
        public double MaximumY { get; set; }

        [DataMember(Order = 6)]
        public double MaximumZ { get; set; }
    }
}
