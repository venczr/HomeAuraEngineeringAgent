using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Net.Http;
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
        [CommandMethod("HA_ANALYZE_MODEL", CommandFlags.Modal)]
        public void AnalyzeModel()
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
                string projectName =
                    GetCurrentProjectName(document);

                AnalysisResponse analysis =
                    RequestAnalysis(projectName);

                WriteAnalysis(editor, analysis);
            }
            catch (AutoCadCommandUserException exception)
            {
                editor.WriteMessage("\n" + exception.SafeMessage);
            }
            catch (AgentApiStartupException exception)
            {
                editor.WriteMessage("\n" + exception.SafeMessage);
            }
            catch (System.Threading.Tasks.TaskCanceledException exception)
            {
                WriteApiTransportError(editor, exception);
            }
            catch (HttpRequestException exception)
            {
                WriteApiTransportError(editor, exception);
            }
            catch (System.Exception)
            {
                editor.WriteMessage(
                    AutoCadCommandDiagnostics.FormatUnexpected(
                        AutoCadCommandOperation.AnalyzeModel
                    )
                );
            }
        }

        [CommandMethod(
            "HA_FIND_REMOTE_OBJECT",
            CommandFlags.Modal)]
        public void FindRemoteObject()
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
                string projectName =
                    GetCurrentProjectName(document);

                AnalysisResponse analysis =
                    RequestAnalysis(projectName);

                AnalysisIssue issue =
                    FindIssue(
                        analysis,
                        "MODEL_EXTENTS_LARGE"
                    );

                List<RemoteEntityDiagnostic> remoteEntities =
                    issue == null ||
                    issue.Details == null
                        ? null
                        : issue.Details.RemoteEntities;

                if (remoteEntities == null ||
                    remoteEntities.Count == 0)
                {
                    editor.WriteMessage(
                        "\nHomeAura не получил пообъектную " +
                        "диагностику."
                    );
                    editor.WriteMessage(
                        "\nСначала выполни HA_SYNC_MODEL " +
                        "обновлённым плагином, затем повтори " +
                        "HA_FIND_REMOTE_OBJECT."
                    );
                    return;
                }

                ObjectResolutionResult resolution =
                    ResolveObjectIds(
                        document.Database,
                        remoteEntities
                    );

                List<ObjectId> objectIds =
                    resolution.ObjectIds;

                string skippedSummary =
                    resolution.Plan.FormatSkippedSummary(
                        resolution.NotFoundCount
                    );

                if (objectIds.Count == 0)
                {
                    if (skippedSummary.Length > 0)
                    {
                        editor.WriteMessage(skippedSummary);
                    }

                    editor.WriteMessage(
                        "\nУдалённые объекты указаны в отчёте, " +
                        "но их Handle не найдены в текущем DWG."
                    );
                    editor.WriteMessage(
                        "\nПовтори HA_SYNC_MODEL и " +
                        "HA_FIND_REMOTE_OBJECT без изменения " +
                        "чертежа между командами."
                    );
                    return;
                }

                Extents3d selectionExtents;
                bool hasExtents =
                    TryGetCombinedExtents(
                        document.Database,
                        objectIds,
                        resolution.Diagnostics,
                        out selectionExtents
                    );

                editor.SetImpliedSelection(
                    objectIds.ToArray()
                );

                if (hasExtents)
                {
                    ZoomToExtents(
                        editor,
                        selectionExtents
                    );
                }

                RemoteEntityDiagnostic first =
                    resolution.Diagnostics[0];

                editor.WriteMessage("\n");
                editor.WriteMessage(
                    "\n===================================="
                );
                editor.WriteMessage(
                    "\n HomeAura — удалённая геометрия"
                );
                editor.WriteMessage(
                    "\n===================================="
                );
                editor.WriteMessage(
                    "\nВыделено объектов: " +
                    objectIds.Count
                );
                if (skippedSummary.Length > 0)
                {
                    editor.WriteMessage(skippedSummary);
                }
                editor.WriteMessage(
                    "\nОсновной Handle: " +
                    AutoCadDisplayText.Format(
                        first.Handle,
                        AutoCadDisplayText.IdentifierLimit
                    )
                );
                editor.WriteMessage(
                    "\nТип: " +
                    AutoCadDisplayText.Format(
                        first.DxfName,
                        AutoCadDisplayText.IdentifierLimit
                    )
                );
                editor.WriteMessage(
                    "\nСлой: " +
                    AutoCadDisplayText.Format(
                        first.Layer,
                        AutoCadDisplayText.NameLimit
                    )
                );
                editor.WriteMessage(
                    "\nРасстояние от помещений: " +
                    FormatDiagnosticNumber(
                        first.DistanceFromRoomMarkersM
                    ) +
                    " м"
                );
                editor.WriteMessage(
                    "\nОбъект выделен и показан на экране."
                );
                editor.WriteMessage(
                    "\nПроверь его перед удалением."
                );
                editor.WriteMessage(
                    "\n===================================="
                );
                editor.WriteMessage("\n");
            }
            catch (AutoCadCommandUserException exception)
            {
                editor.WriteMessage("\n" + exception.SafeMessage);
            }
            catch (AgentApiStartupException exception)
            {
                editor.WriteMessage("\n" + exception.SafeMessage);
            }
            catch (System.Threading.Tasks.TaskCanceledException exception)
            {
                WriteApiTransportError(editor, exception);
            }
            catch (HttpRequestException exception)
            {
                WriteApiTransportError(editor, exception);
            }
            catch (System.Exception)
            {
                editor.WriteMessage(
                    AutoCadCommandDiagnostics.FormatUnexpected(
                        AutoCadCommandOperation.FindRemoteObject
                    )
                );
            }
        }

        private static string GetCurrentProjectName(
            Document document)
        {
            if (string.IsNullOrWhiteSpace(document.Name) ||
                !Path.IsPathRooted(document.Name))
            {
                throw new AutoCadCommandUserException(
                    "Сначала сохрани DWG на диск."
                );
            }

            string drawingDirectory =
                Path.GetDirectoryName(document.Name);

            if (string.IsNullOrWhiteSpace(drawingDirectory))
            {
                throw new AutoCadCommandUserException(
                    "Не удалось определить папку проекта."
                );
            }

            return new DirectoryInfo(
                drawingDirectory
            ).Name;
        }

        private static AnalysisResponse RequestAnalysis(
            string projectName)
        {
            string apiMessage;

            if (!AgentApiProcessManager.EnsureRunning(
                    out apiMessage))
            {
                throw new AgentApiStartupException(apiMessage);
            }

            string endpoint =
                "http://127.0.0.1:8765" +
                "/api/v1/projects/" +
                Uri.EscapeDataString(projectName) +
                "/analyze";

            using (HttpRequestMessage request =
                   new HttpRequestMessage(
                       HttpMethod.Post,
                       endpoint
                   ))
            using (HttpResponseMessage response =
                   SyncHttpClient
                       .SendAsync(
                           request,
                           HttpCompletionOption
                               .ResponseHeadersRead
                       )
                       .GetAwaiter()
                       .GetResult())
            {
                if (!response.IsSuccessStatusCode)
                {
                    throw new AutoCadCommandUserException(
                        ApiResponseDiagnostics.FormatFailure(
                            response.StatusCode
                        )
                    );
                }

                byte[] responseBytes;
                try
                {
                    responseBytes =
                        BoundedHttpContentReader.Read(
                            response.Content,
                            BoundedHttpContentReader
                                .AnalysisResponseMaximumBytes
                        );
                }
                catch (HttpContentLimitExceededException)
                {
                    throw new AutoCadCommandUserException(
                        "Ответ HomeAura API превышает 10 MiB."
                    );
                }

                return DeserializeAnalysis(responseBytes);
            }
        }

        private static void WriteAnalysis(
            Editor editor,
            AnalysisResponse analysis)
        {
            editor.WriteMessage("\n");
            editor.WriteMessage(
                "\n===================================="
            );
            editor.WriteMessage(
                "\n HomeAura — анализ модели"
            );
            editor.WriteMessage(
                "\n===================================="
            );
            editor.WriteMessage(
                "\nПроект: " +
                AutoCadDisplayText.Format(
                    analysis.Project,
                    AutoCadDisplayText.NameLimit
                )
            );
            editor.WriteMessage(
                "\nЧертёж: " +
                AutoCadDisplayText.Format(
                    analysis.Drawing,
                    AutoCadDisplayText.NameLimit
                )
            );
            editor.WriteMessage(
                "\nРезультат: " +
                AutoCadDisplayText.Format(
                    analysis.Status,
                    AutoCadDisplayText.IdentifierLimit
                )
            );
            editor.WriteMessage(
                "\nОценка: " + analysis.Score + "/100"
            );
            editor.WriteMessage(
                "\nОшибок: " + analysis.Errors
            );
            editor.WriteMessage(
                "\nПредупреждений: " +
                analysis.Warnings
            );
            editor.WriteMessage(
                "\nИнформационных проверок: " +
                analysis.Infos
            );

            if (analysis.Issues != null)
            {
                editor.WriteMessage(
                    "\n\nРезультаты проверок:"
                );

                int limit = Math.Min(
                    analysis.Issues.Count,
                    15
                );

                for (int index = 0;
                     index < limit;
                     index++)
                {
                    AnalysisIssue issue =
                        analysis.Issues[index];

                    string rawSeverity =
                        issue == null
                            ? null
                            : issue.Severity;

                    string severity =
                        string.IsNullOrWhiteSpace(
                            rawSeverity)
                            ? "INFO"
                            : AutoCadDisplayText.Format(
                                rawSeverity,
                                AutoCadDisplayText
                                    .IdentifierLimit
                            )
                                .ToUpperInvariant();

                    editor.WriteMessage(
                        "\n[" +
                        severity +
                        "] " +
                        AutoCadDisplayText.Format(
                            issue == null
                                ? null
                                : issue.Code,
                            AutoCadDisplayText.IdentifierLimit
                        ) +
                        ": " +
                        AutoCadDisplayText.Format(
                            issue == null
                                ? null
                                : issue.Message,
                            AutoCadDisplayText.MessageLimit
                        )
                    );
                }
            }

            AnalysisIssue remoteIssue =
                FindIssue(
                    analysis,
                    "MODEL_EXTENTS_LARGE"
                );

            if (remoteIssue != null &&
                remoteIssue.Details != null &&
                remoteIssue.Details.RemoteEntities != null &&
                remoteIssue.Details.RemoteEntities.Count > 0 &&
                remoteIssue.Details.RemoteEntities[0] != null)
            {
                RemoteEntityDiagnostic remote =
                    remoteIssue.Details.RemoteEntities[0];

                editor.WriteMessage(
                    "\n\nВероятный удалённый объект:"
                );
                editor.WriteMessage(
                    "\nHandle: " +
                    AutoCadDisplayText.Format(
                        remote.Handle,
                        AutoCadDisplayText.IdentifierLimit
                    )
                );
                editor.WriteMessage(
                    "\nТип: " +
                    AutoCadDisplayText.Format(
                        remote.DxfName,
                        AutoCadDisplayText.IdentifierLimit
                    )
                );
                editor.WriteMessage(
                    "\nСлой: " +
                    AutoCadDisplayText.Format(
                        remote.Layer,
                        AutoCadDisplayText.NameLimit
                    )
                );
                editor.WriteMessage(
                    "\nРасстояние: " +
                    FormatDiagnosticNumber(
                        remote.DistanceFromRoomMarkersM
                    ) +
                    " м"
                );
                editor.WriteMessage(
                    "\nКоманда выделения: " +
                    "HA_FIND_REMOTE_OBJECT"
                );
            }

            editor.WriteMessage(
                "\n\nОтчёт: " +
                AutoCadDisplayText.Format(
                    analysis.ReportPath,
                    AutoCadDisplayText.PathLimit
                )
            );
            editor.WriteMessage(
                "\n===================================="
            );
            editor.WriteMessage("\n");
        }

        private static AnalysisIssue FindIssue(
            AnalysisResponse analysis,
            string code)
        {
            if (analysis == null ||
                analysis.Issues == null)
            {
                return null;
            }

            foreach (AnalysisIssue issue in analysis.Issues)
            {
                if (issue != null &&
                    string.Equals(
                        issue.Code,
                        code,
                        StringComparison.OrdinalIgnoreCase))
                {
                    return issue;
                }
            }

            return null;
        }

        private sealed class ObjectResolutionResult
        {
            public ObjectResolutionResult(
                RemoteHandleSelectionPlan plan)
            {
                Plan = plan;
                ObjectIds = new List<ObjectId>();
                Diagnostics =
                    new List<RemoteEntityDiagnostic>();
            }

            public RemoteHandleSelectionPlan Plan
            {
                get;
                private set;
            }

            public List<ObjectId> ObjectIds
            {
                get;
                private set;
            }

            public List<RemoteEntityDiagnostic> Diagnostics
            {
                get;
                private set;
            }

            public int NotFoundCount
            {
                get;
                set;
            }
        }

        private static ObjectResolutionResult ResolveObjectIds(
            Database database,
            IList<RemoteEntityDiagnostic> diagnostics)
        {
            List<string> handles = new List<string>();

            foreach (RemoteEntityDiagnostic diagnostic
                      in diagnostics)
            {
                handles.Add(
                    diagnostic == null
                        ? null
                        : diagnostic.Handle
                );
            }

            RemoteHandleSelectionPlan plan =
                RemoteHandleSelectionPlan.Create(handles);
            ObjectResolutionResult result =
                new ObjectResolutionResult(plan);

            foreach (RemoteHandleCandidate candidate
                      in plan.Candidates)
            {
                ObjectId objectId;

                try
                {
                    objectId =
                        database.GetObjectId(
                            false,
                            new Handle(candidate.HandleValue),
                            0
                        );
                }
                catch (Autodesk.AutoCAD.Runtime.Exception)
                {
                    result.NotFoundCount++;
                    continue;
                }

                if (objectId.IsNull || objectId.IsErased)
                {
                    result.NotFoundCount++;
                    continue;
                }

                result.ObjectIds.Add(objectId);
                result.Diagnostics.Add(
                    diagnostics[candidate.DiagnosticIndex]
                );
            }

            return result;
        }

        private static bool TryGetCombinedExtents(
            Database database,
            IList<ObjectId> objectIds,
            IList<RemoteEntityDiagnostic> diagnostics,
            out Extents3d combinedExtents)
        {
            combinedExtents = new Extents3d();
            bool hasExtents = false;

            using (Transaction transaction =
                   database.TransactionManager
                       .StartTransaction())
            {
                foreach (ObjectId objectId in objectIds)
                {
                    Entity entity =
                        transaction.GetObject(
                            objectId,
                            OpenMode.ForRead,
                            false
                        ) as Entity;

                    if (entity == null)
                    {
                        continue;
                    }

                    try
                    {
                        Extents3d rawExtents =
                            entity.GeometricExtents;
                        Extents3d entityExtents =
                            CreateCheckedExtents(
                                rawExtents.MinPoint,
                                rawExtents.MaxPoint,
                                "Analyze.LiveExtents"
                            );

                        if (!hasExtents)
                        {
                            combinedExtents =
                                entityExtents;
                            hasExtents = true;
                        }
                        else
                        {
                            combinedExtents.AddExtents(
                                entityExtents
                            );
                        }
                    }
                    catch
                    {
                        // Используем границы из отчёта ниже.
                    }
                }

                transaction.Commit();
            }

            if (hasExtents)
            {
                return true;
            }

            foreach (RemoteEntityDiagnostic diagnostic
                     in diagnostics)
            {
                if (diagnostic == null ||
                    diagnostic.Extents == null ||
                    diagnostic.Extents.Minimum == null ||
                    diagnostic.Extents.Maximum == null)
                {
                    continue;
                }

                PointSnapshot minimum =
                    diagnostic.Extents.Minimum;

                PointSnapshot maximum =
                    diagnostic.Extents.Maximum;

                Extents3d entityExtents =
                    CreateCheckedExtents(
                        new Point3d(
                            minimum.X,
                            minimum.Y,
                            minimum.Z
                        ),
                        new Point3d(
                            maximum.X,
                            maximum.Y,
                            maximum.Z
                        ),
                        "Analyze.ReportExtents"
                    );

                if (!hasExtents)
                {
                    combinedExtents = entityExtents;
                    hasExtents = true;
                }
                else
                {
                    combinedExtents.AddExtents(
                        entityExtents
                    );
                }
            }

            return hasExtents;
        }

        private static Extents3d CreateCheckedExtents(
            Point3d minimum,
            Point3d maximum,
            string fieldName)
        {
            EngineeringNumericGuard.RequireFinite(
                minimum.X,
                fieldName + ".Minimum.X"
            );
            EngineeringNumericGuard.RequireFinite(
                minimum.Y,
                fieldName + ".Minimum.Y"
            );
            EngineeringNumericGuard.RequireFinite(
                minimum.Z,
                fieldName + ".Minimum.Z"
            );
            EngineeringNumericGuard.RequireFinite(
                maximum.X,
                fieldName + ".Maximum.X"
            );
            EngineeringNumericGuard.RequireFinite(
                maximum.Y,
                fieldName + ".Maximum.Y"
            );
            EngineeringNumericGuard.RequireFinite(
                maximum.Z,
                fieldName + ".Maximum.Z"
            );

            return new Extents3d(minimum, maximum);
        }

        private static void ZoomToExtents(
            Editor editor,
            Extents3d worldExtents)
        {
            using (ViewTableRecord view =
                   editor.GetCurrentView())
            {
                Matrix3d worldToDisplay =
                    Matrix3d.PlaneToWorld(
                        view.ViewDirection
                    );

                worldToDisplay =
                    Matrix3d.Displacement(
                        view.Target -
                        Point3d.Origin
                    ) *
                    worldToDisplay;

                worldToDisplay =
                    Matrix3d.Rotation(
                        -view.ViewTwist,
                        view.ViewDirection,
                        view.Target
                    ) *
                    worldToDisplay;

                worldToDisplay =
                    worldToDisplay.Inverse();

                Point3d minimum =
                    worldExtents.MinPoint
                        .TransformBy(worldToDisplay);

                Point3d maximum =
                    worldExtents.MaxPoint
                        .TransformBy(worldToDisplay);

                double width =
                    EngineeringNumericGuard.ScaledSpan(
                        minimum.X,
                        maximum.X,
                        1000.0,
                        1.5,
                        "Analyze.Zoom.Width"
                    );

                double height =
                    EngineeringNumericGuard.ScaledSpan(
                        minimum.Y,
                        maximum.Y,
                        1000.0,
                        1.5,
                        "Analyze.Zoom.Height"
                    );

                double viewWidth =
                    EngineeringNumericGuard
                        .RequirePositiveFinite(
                            view.Width,
                            "Analyze.View.Width"
                        );
                double viewHeight =
                    EngineeringNumericGuard.RequireFinite(
                        view.Height,
                        "Analyze.View.Height"
                    );

                double viewRatio =
                    EngineeringNumericGuard
                        .RequirePositiveFinite(
                            viewWidth /
                            Math.Max(
                                viewHeight,
                                0.000001
                            ),
                            "Analyze.View.Ratio"
                        );

                double selectionRatio =
                    EngineeringNumericGuard
                        .RequirePositiveFinite(
                            width / height,
                            "Analyze.Zoom.SelectionRatio"
                        );

                if (selectionRatio > viewRatio)
                {
                    height =
                        EngineeringNumericGuard
                            .RequirePositiveFinite(
                                width / viewRatio,
                                "Analyze.Zoom.AdjustedHeight"
                            );
                }
                else
                {
                    width =
                        EngineeringNumericGuard
                            .RequirePositiveFinite(
                                height * viewRatio,
                                "Analyze.Zoom.AdjustedWidth"
                            );
                }

                view.CenterPoint =
                    new Point2d(
                        EngineeringNumericGuard.Midpoint(
                            minimum.X,
                            maximum.X,
                            "Analyze.Zoom.Center.X"
                        ),
                        EngineeringNumericGuard.Midpoint(
                            minimum.Y,
                            maximum.Y,
                            "Analyze.Zoom.Center.Y"
                        )
                    );

                view.Width = width;
                view.Height = height;

                editor.SetCurrentView(view);
            }
        }

        private static string FormatDiagnosticNumber(
            double value)
        {
            return value.ToString(
                "0.###",
                CultureInfo.InvariantCulture
            );
        }

        private static void WriteApiTransportError(
            Editor editor,
            System.Exception exception)
        {
            editor.WriteMessage(
                "\n" +
                ApiResponseDiagnostics
                    .FormatTransportFailure(exception)
            );
            editor.WriteMessage(
                "\nПроверь сервер: " +
                "http://127.0.0.1:8765"
            );
        }

        private static AnalysisResponse DeserializeAnalysis(
            byte[] bytes)
        {
            DataContractJsonSerializer serializer =
                new DataContractJsonSerializer(
                    typeof(AnalysisResponse)
                );

            using (MemoryStream stream =
                   new MemoryStream(bytes))
            {
                return (AnalysisResponse)
                    serializer.ReadObject(stream);
            }
        }
    }

    [DataContract]
    public sealed class AnalysisResponse
    {
        [DataMember(Name = "status")]
        public string Status { get; set; }

        [DataMember(Name = "project")]
        public string Project { get; set; }

        [DataMember(Name = "drawing")]
        public string Drawing { get; set; }

        [DataMember(Name = "score")]
        public int Score { get; set; }

        [DataMember(Name = "errors")]
        public int Errors { get; set; }

        [DataMember(Name = "warnings")]
        public int Warnings { get; set; }

        [DataMember(Name = "infos")]
        public int Infos { get; set; }

        [DataMember(Name = "issues")]
        public List<AnalysisIssue> Issues { get; set; }

        [DataMember(Name = "report_path")]
        public string ReportPath { get; set; }

        [DataMember(Name = "history_path")]
        public string HistoryPath { get; set; }
    }

    [DataContract]
    public sealed class AnalysisIssue
    {
        [DataMember(Name = "severity")]
        public string Severity { get; set; }

        [DataMember(Name = "code")]
        public string Code { get; set; }

        [DataMember(Name = "message")]
        public string Message { get; set; }

        [DataMember(Name = "details")]
        public AnalysisIssueDetails Details { get; set; }
    }

    [DataContract]
    public sealed class AnalysisIssueDetails
    {
        [DataMember(Name = "axis")]
        public string Axis { get; set; }

        [DataMember(Name = "far_side")]
        public string FarSide { get; set; }

        [DataMember(Name = "far_coordinate_mm")]
        public double? FarCoordinateMm { get; set; }

        [DataMember(Name = "gap_from_room_markers_m")]
        public double? GapFromRoomMarkersM { get; set; }

        [DataMember(Name = "entity_diagnostics_available")]
        public bool? EntityDiagnosticsAvailable { get; set; }

        [DataMember(Name = "remote_entity_count")]
        public int? RemoteEntityCount { get; set; }

        [DataMember(Name = "remote_entities")]
        public List<RemoteEntityDiagnostic> RemoteEntities { get; set; }
    }

    [DataContract]
    public sealed class RemoteEntityDiagnostic
    {
        [DataMember(Name = "handle")]
        public string Handle { get; set; }

        [DataMember(Name = "dxf_name")]
        public string DxfName { get; set; }

        [DataMember(Name = "rx_class_name")]
        public string RxClassName { get; set; }

        [DataMember(Name = "dotnet_type")]
        public string DotNetType { get; set; }

        [DataMember(Name = "layer")]
        public string Layer { get; set; }

        [DataMember(Name = "extents")]
        public ExtentsSnapshot Extents { get; set; }

        [DataMember(Name = "center")]
        public PointSnapshot Center { get; set; }

        [DataMember(Name = "distance_from_room_markers_mm")]
        public double DistanceFromRoomMarkersMm { get; set; }

        [DataMember(Name = "distance_from_room_markers_m")]
        public double DistanceFromRoomMarkersM { get; set; }
    }
}
