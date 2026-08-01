using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;

using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Geometry;
using Autodesk.AutoCAD.Runtime;

[assembly: ExtensionApplication(typeof(HomeAura.AutoCAD.Agent.Plugin))]
[assembly: CommandClass(typeof(HomeAura.AutoCAD.Agent.Commands))]

namespace HomeAura.AutoCAD.Agent
{
    public sealed class Plugin : IExtensionApplication
    {
        public void Initialize()
        {
            string apiMessage;

            bool apiReady =
                AgentApiProcessManager.EnsureRunning(
                    out apiMessage
                );

            Document document =
                Application.DocumentManager.MdiActiveDocument;

            if (document == null)
            {
                return;
            }

            document.Editor.WriteMessage("\n");
            document.Editor.WriteMessage(
                "\nHomeAura AutoCAD Agent загружен."
            );

            document.Editor.WriteMessage(
                "\nHomeAura API: " +
                (apiReady ? "готов" : "ошибка")
            );

            document.Editor.WriteMessage(
                "\n" + apiMessage
            );

            document.Editor.WriteMessage(
    "\nКоманды: HA_STATUS, HA_API_STATUS, " +
    "HA_SYNC_MODEL, HA_SYNC_ROOMS, " +
    "HA_ANALYZE_MODEL, HA_FIND_REMOTE_OBJECT, " +
    "HA_DISCOVER_ROOM_BOUNDARIES, " +
    "HA_EXPORT_ROOMS."
);

            document.Editor.WriteMessage("\n");
        }

        public void Terminate()
        {
            // Освобождение ресурсов добавим позже.
        }
    }

    public sealed partial class Commands
    {
        [CommandMethod("HA_STATUS", CommandFlags.Modal)]
        public void ShowStatus()
        {
            Document document =
                Application.DocumentManager.MdiActiveDocument;

            if (document == null)
            {
                return;
            }

            Editor editor = document.Editor;

            string pluginVersion =
                Assembly.GetExecutingAssembly()
                    .GetName()
                    .Version
                    .ToString();

            string drawingName = string.IsNullOrWhiteSpace(document.Name)
                ? "Новый несохранённый чертёж"
                : Path.GetFileName(document.Name);

            object acadVersion =
                Application.GetSystemVariable("ACADVER");

            editor.WriteMessage("\n");
            editor.WriteMessage("\n====================================");
            editor.WriteMessage("\n HomeAura Engineering Agent");
            editor.WriteMessage("\n====================================");
            editor.WriteMessage("\nПлагин загружен: Да");
            editor.WriteMessage(
                "\nВерсия плагина: " + pluginVersion
            );
            editor.WriteMessage(
                "\nAutoCAD ACADVER: " + acadVersion
            );
            editor.WriteMessage(
                "\n64-битный процесс: " +
                Environment.Is64BitProcess
            );
            editor.WriteMessage(
                "\nТекущий чертёж: " + drawingName
            );
            editor.WriteMessage("\n====================================");
            editor.WriteMessage("\n");
        }

        [CommandMethod("HA_EXPORT_MODEL", CommandFlags.Modal)]
        public void ExportModel()
        {
            Document document =
                Application.DocumentManager.MdiActiveDocument;

            if (document == null)
            {
                return;
            }

            Editor editor = document.Editor;
            Database database = document.Database;

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

                ModelSnapshot snapshot =
                    ReadModel(document, database);

                string drawingDirectory =
                    Path.GetDirectoryName(document.Name);

                if (string.IsNullOrWhiteSpace(drawingDirectory))
                {
                    throw new InvalidOperationException(
                        "Не удалось определить папку DWG."
                    );
                }

                string exportDirectory =
                    Path.Combine(drawingDirectory, "exports");

                string exportPath =
                    Path.Combine(
                        exportDirectory,
                        "model_snapshot.json"
                    );

                WriteJson(
                    drawingDirectory,
                    exportPath,
                    snapshot
                );

                editor.WriteMessage("\n");
                editor.WriteMessage(
                    "\nHomeAura: снимок модели создан."
                );
                editor.WriteMessage(
                    "\nОбъектов в модели: " +
                    snapshot.ModelSpaceEntityCount
                );
                editor.WriteMessage(
                    "\nСлоёв: " + snapshot.Layers.Count
                );
                editor.WriteMessage(
                    "\nТипов объектов: " +
                    snapshot.EntityTypes.Count
                );
                editor.WriteMessage(
                    "\nБлоков: " +
                    snapshot.BlockDefinitions.Count
                );
                editor.WriteMessage(
                    "\nJSON: " + exportPath
                );
                editor.WriteMessage("\n");
            }
            catch (System.Exception)
            {
                editor.WriteMessage(
                    AutoCadCommandDiagnostics.FormatUnexpected(
                        AutoCadCommandOperation.ExportModel
                    )
                );
            }
        }

        private static ModelSnapshot ReadModel(
            Document document,
            Database database)
        {
            try
            {
                database.UpdateExt(true);
            }
            catch
            {
                // Для пустого или особого чертежа
                // границы могут быть недоступны.
            }

            ModelSnapshot snapshot = new ModelSnapshot
            {
                GeneratedAtUtc =
                    DateTime.UtcNow.ToString("O"),

                DrawingName =
                    Path.GetFileName(document.Name),

                DrawingFullPath =
                    document.Name,

                AcadVersion =
                    Convert.ToString(
                        Application.GetSystemVariable("ACADVER")
                    ),

                PluginVersion =
                    Assembly.GetExecutingAssembly()
                        .GetName()
                        .Version
                        .ToString(),

                Is64BitProcess =
                    Environment.Is64BitProcess,

                DrawingUnits =
                    database.Insunits.ToString(),

                Extents =
                    CreateExtents(database.Extmin, database.Extmax),

                Layers =
                    new List<LayerSnapshot>(),

                EntityTypes =
                    new List<EntityTypeSnapshot>(),

                Entities =
                    new List<EntitySnapshot>(),

                BlockDefinitions =
                    new List<BlockSnapshot>()
            };

            Dictionary<string, EntityTypeSnapshot> entityTypeMap =
                new Dictionary<string, EntityTypeSnapshot>(
                    StringComparer.OrdinalIgnoreCase
                );

            using (Transaction transaction =
                   database.TransactionManager.StartTransaction())
            {
                LayerTable layerTable =
                    (LayerTable)transaction.GetObject(
                        database.LayerTableId,
                        OpenMode.ForRead
                    );

                foreach (ObjectId layerId in layerTable)
                {
                    LayerTableRecord layer =
                        (LayerTableRecord)transaction.GetObject(
                            layerId,
                            OpenMode.ForRead
                        );

                    snapshot.Layers.Add(
                        new LayerSnapshot
                        {
                            Name = layer.Name,
                            IsOff = layer.IsOff,
                            IsFrozen = layer.IsFrozen,
                            IsLocked = layer.IsLocked,
                            ColorIndex = layer.Color.ColorIndex
                        }
                    );
                }

                BlockTable blockTable =
                    (BlockTable)transaction.GetObject(
                        database.BlockTableId,
                        OpenMode.ForRead
                    );

                BlockTableRecord modelSpace =
                    (BlockTableRecord)transaction.GetObject(
                        blockTable[BlockTableRecord.ModelSpace],
                        OpenMode.ForRead
                    );

                foreach (ObjectId objectId in modelSpace)
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

                    RXClass rxClass =
                        databaseObject.GetRXClass();

                    string dxfName =
                        rxClass == null
                            ? "UNKNOWN"
                            : rxClass.DxfName;

                    string rxName =
                        rxClass == null
                            ? "UNKNOWN"
                            : rxClass.Name;

                    string dotNetType =
                        databaseObject.GetType().FullName ??
                        databaseObject.GetType().Name;

                    string key =
                        dxfName + "|" +
                        rxName + "|" +
                        dotNetType;

                    Entity entity =
                        databaseObject as Entity;

                    ExtentsSnapshot entityExtents =
                        TryCreateEntityExtents(entity);

                    snapshot.Entities.Add(
                        new EntitySnapshot
                        {
                            Handle = GetHandle(databaseObject),
                            DxfName = dxfName,
                            RxClassName = rxName,
                            DotNetType = dotNetType,
                            Layer = GetLayerName(entity),
                            HasGeometricExtents =
                                entityExtents != null,
                            Extents = entityExtents,
                            Center =
                                CreateCenter(entityExtents)
                        }
                    );

                    EntityTypeSnapshot typeSnapshot;

                    if (!entityTypeMap.TryGetValue(
                            key,
                            out typeSnapshot))
                    {
                        typeSnapshot =
                            new EntityTypeSnapshot
                            {
                                DxfName = dxfName,
                                RxClassName = rxName,
                                DotNetType = dotNetType,
                                Count = 0
                            };

                        entityTypeMap.Add(
                            key,
                            typeSnapshot
                        );
                    }

                    typeSnapshot.Count++;
                    snapshot.ModelSpaceEntityCount++;
                }

                foreach (ObjectId blockId in blockTable)
                {
                    BlockTableRecord block =
                        (BlockTableRecord)transaction.GetObject(
                            blockId,
                            OpenMode.ForRead
                        );

                    if (block.IsLayout)
                    {
                        continue;
                    }

                    snapshot.BlockDefinitions.Add(
                        new BlockSnapshot
                        {
                            Name = block.Name,
                            EntityCount =
                                block.Cast<ObjectId>().Count(),
                            IsAnonymous = block.IsAnonymous,
                            IsExternalReference =
                                block.IsFromExternalReference
                        }
                    );
                }

                transaction.Commit();
            }

            snapshot.Layers =
                snapshot.Layers
                    .OrderBy(item => item.Name)
                    .ToList();

            snapshot.EntityTypes =
                entityTypeMap.Values
                    .OrderByDescending(item => item.Count)
                    .ThenBy(item => item.DxfName)
                    .ToList();

            snapshot.Entities =
                snapshot.Entities
                    .OrderBy(item => item.Layer)
                    .ThenBy(item => item.Handle)
                    .ToList();

            snapshot.BlockDefinitions =
                snapshot.BlockDefinitions
                    .OrderBy(item => item.Name)
                    .ToList();

            return snapshot;
        }

        private static string GetHandle(
            DBObject databaseObject)
        {
            try
            {
                return databaseObject.Handle.ToString();
            }
            catch
            {
                return string.Empty;
            }
        }

        private static string GetLayerName(
            Entity entity)
        {
            if (entity == null)
            {
                return string.Empty;
            }

            try
            {
                return entity.Layer ?? string.Empty;
            }
            catch
            {
                return string.Empty;
            }
        }

        private static ExtentsSnapshot TryCreateEntityExtents(
            Entity entity)
        {
            if (entity == null)
            {
                return null;
            }

            try
            {
                Extents3d extents =
                    entity.GeometricExtents;

                return CreateExtents(
                    extents.MinPoint,
                    extents.MaxPoint
                );
            }
            catch
            {
                // Некоторые proxy-объекты не предоставляют
                // геометрические границы через AutoCAD API.
                return null;
            }
        }

        private static PointSnapshot CreateCenter(
            ExtentsSnapshot extents)
        {
            if (extents == null ||
                extents.Minimum == null ||
                extents.Maximum == null)
            {
                return null;
            }

            return new PointSnapshot
            {
                X =
                    EngineeringNumericGuard.Midpoint(
                        extents.Minimum.X,
                        extents.Maximum.X,
                        "Entity.Center.X"
                    ),
                Y =
                    EngineeringNumericGuard.Midpoint(
                        extents.Minimum.Y,
                        extents.Maximum.Y,
                        "Entity.Center.Y"
                    ),
                Z =
                    EngineeringNumericGuard.Midpoint(
                        extents.Minimum.Z,
                        extents.Maximum.Z,
                        "Entity.Center.Z"
                    )
            };
        }

        private static ExtentsSnapshot CreateExtents(
            Point3d minimum,
            Point3d maximum)
        {
            EngineeringNumericGuard.RequireFinite(
                minimum.X,
                "Extents.Minimum.X"
            );
            EngineeringNumericGuard.RequireFinite(
                minimum.Y,
                "Extents.Minimum.Y"
            );
            EngineeringNumericGuard.RequireFinite(
                minimum.Z,
                "Extents.Minimum.Z"
            );
            EngineeringNumericGuard.RequireFinite(
                maximum.X,
                "Extents.Maximum.X"
            );
            EngineeringNumericGuard.RequireFinite(
                maximum.Y,
                "Extents.Maximum.Y"
            );
            EngineeringNumericGuard.RequireFinite(
                maximum.Z,
                "Extents.Maximum.Z"
            );

            return new ExtentsSnapshot
            {
                Minimum = new PointSnapshot
                {
                    X = minimum.X,
                    Y = minimum.Y,
                    Z = minimum.Z
                },

                Maximum = new PointSnapshot
                {
                    X = maximum.X,
                    Y = maximum.Y,
                    Z = maximum.Z
                }
            };
        }

        private static void WriteJson(
            string trustedRoot,
            string path,
            ModelSnapshot snapshot)
        {
            DataContractJsonSerializerSettings settings =
                new DataContractJsonSerializerSettings
                {
                    UseSimpleDictionaryFormat = true
                };

            DataContractJsonSerializer serializer =
                new DataContractJsonSerializer(
                    typeof(ModelSnapshot),
                    settings
                );

            AtomicFileWriter.Write(
                trustedRoot,
                path,
                delegate(Stream stream)
                {
                    serializer.WriteObject(
                        stream,
                        snapshot
                    );
                }
            );
        }
    }

    [DataContract]
    public sealed class ModelSnapshot
    {
        [DataMember(Order = 1)]
        public string GeneratedAtUtc { get; set; }

        [DataMember(Order = 2)]
        public string DrawingName { get; set; }

        [DataMember(Order = 3)]
        public string DrawingFullPath { get; set; }

        [DataMember(Order = 4)]
        public string AcadVersion { get; set; }

        [DataMember(Order = 5)]
        public string PluginVersion { get; set; }

        [DataMember(Order = 6)]
        public bool Is64BitProcess { get; set; }

        [DataMember(Order = 7)]
        public string DrawingUnits { get; set; }

        [DataMember(Order = 8)]
        public ExtentsSnapshot Extents { get; set; }

        [DataMember(Order = 9)]
        public int ModelSpaceEntityCount { get; set; }

        [DataMember(Order = 10)]
        public List<LayerSnapshot> Layers { get; set; }

        [DataMember(Order = 11)]
        public List<EntityTypeSnapshot> EntityTypes { get; set; }

        [DataMember(Order = 12)]
        public List<BlockSnapshot> BlockDefinitions { get; set; }

        [DataMember(Order = 13)]
        public List<EntitySnapshot> Entities { get; set; }
    }

    [DataContract]
    public sealed class PointSnapshot
    {
        [DataMember(Order = 1)]
        public double X { get; set; }

        [DataMember(Order = 2)]
        public double Y { get; set; }

        [DataMember(Order = 3)]
        public double Z { get; set; }
    }

    [DataContract]
    public sealed class ExtentsSnapshot
    {
        [DataMember(Order = 1)]
        public PointSnapshot Minimum { get; set; }

        [DataMember(Order = 2)]
        public PointSnapshot Maximum { get; set; }
    }

    [DataContract]
    public sealed class LayerSnapshot
    {
        [DataMember(Order = 1)]
        public string Name { get; set; }

        [DataMember(Order = 2)]
        public bool IsOff { get; set; }

        [DataMember(Order = 3)]
        public bool IsFrozen { get; set; }

        [DataMember(Order = 4)]
        public bool IsLocked { get; set; }

        [DataMember(Order = 5)]
        public short ColorIndex { get; set; }
    }

    [DataContract]
    public sealed class EntityTypeSnapshot
    {
        [DataMember(Order = 1)]
        public string DxfName { get; set; }

        [DataMember(Order = 2)]
        public string RxClassName { get; set; }

        [DataMember(Order = 3)]
        public string DotNetType { get; set; }

        [DataMember(Order = 4)]
        public int Count { get; set; }
    }

    [DataContract]
    public sealed class EntitySnapshot
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
        public bool HasGeometricExtents { get; set; }

        [DataMember(Order = 7)]
        public ExtentsSnapshot Extents { get; set; }

        [DataMember(Order = 8)]
        public PointSnapshot Center { get; set; }
    }

    [DataContract]
    public sealed class BlockSnapshot
    {
        [DataMember(Order = 1)]
        public string Name { get; set; }

        [DataMember(Order = 2)]
        public int EntityCount { get; set; }

        [DataMember(Order = 3)]
        public bool IsAnonymous { get; set; }

        [DataMember(Order = 4)]
        public bool IsExternalReference { get; set; }
    }
}
