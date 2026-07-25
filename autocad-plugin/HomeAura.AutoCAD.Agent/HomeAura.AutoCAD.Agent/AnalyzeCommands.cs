using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Text;

using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.EditorInput;
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
                if (string.IsNullOrWhiteSpace(document.Name) ||
                    !Path.IsPathRooted(document.Name))
                {
                    editor.WriteMessage(
                        "\nСначала сохрани DWG на диск."
                    );
                    return;
                }

                string drawingDirectory =
                    Path.GetDirectoryName(document.Name);

                if (string.IsNullOrWhiteSpace(drawingDirectory))
                {
                    throw new InvalidOperationException(
                        "Не удалось определить папку проекта."
                    );
                }

                string projectName =
                    new DirectoryInfo(drawingDirectory).Name;

                ModelSnapshot snapshot =
                    ReadModel(
                        document,
                        document.Database
                    );

                string json =
                    SerializeSnapshot(snapshot);

                string endpoint =
                    "http://127.0.0.1:8765" +
                    "/api/v1/projects/" +
                    Uri.EscapeDataString(projectName) +
                    "/analyze";

                string responseText;

                using (StringContent content =
                       new StringContent(
                           json,
                           Encoding.UTF8,
                           "application/json"))
                {
                    HttpResponseMessage response =
                        SyncHttpClient
                            .PostAsync(endpoint, content)
                            .GetAwaiter()
                            .GetResult();

                    responseText =
                        response.Content
                            .ReadAsStringAsync()
                            .GetAwaiter()
                            .GetResult();

                    if (!response.IsSuccessStatusCode)
                    {
                        editor.WriteMessage(
                            "\nHomeAura API вернул ошибку: " +
                            (int)response.StatusCode +
                            " " +
                            response.ReasonPhrase
                        );

                        editor.WriteMessage(
                            "\nОтвет сервера: " +
                            responseText
                        );

                        return;
                    }
                }

                AnalysisResponse analysis =
                    DeserializeAnalysis(responseText);

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
                    "\nПроект: " + analysis.Project
                );
                editor.WriteMessage(
                    "\nЧертёж: " + analysis.Drawing
                );
                editor.WriteMessage(
                    "\nРезультат: " + analysis.Status
                );
                editor.WriteMessage(
                    "\nОценка: " + analysis.Score + "/100"
                );
                editor.WriteMessage(
                    "\nОшибок: " + analysis.Errors
                );
                editor.WriteMessage(
                    "\nПредупреждений: " + analysis.Warnings
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

                        editor.WriteMessage(
                            "\n[" +
                            issue.Severity.ToUpperInvariant() +
                            "] " +
                            issue.Code +
                            ": " +
                            issue.Message
                        );
                    }
                }

                editor.WriteMessage(
                    "\n\nОтчёт: " + analysis.ReportPath
                );
                editor.WriteMessage(
                    "\n===================================="
                );
                editor.WriteMessage("\n");
            }
            catch (HttpRequestException exception)
            {
                editor.WriteMessage(
                    "\nНе удалось подключиться к HomeAura API."
                );
                editor.WriteMessage(
                    "\nПроверь сервер: " +
                    "http://127.0.0.1:8765"
                );
                editor.WriteMessage(
                    "\nОшибка: " + exception.Message
                );
            }
            catch (System.Exception exception)
            {
                editor.WriteMessage(
                    "\nОшибка HA_ANALYZE_MODEL: " +
                    exception.Message
                );
            }
        }

        private static AnalysisResponse DeserializeAnalysis(
            string json)
        {
            DataContractJsonSerializer serializer =
                new DataContractJsonSerializer(
                    typeof(AnalysisResponse)
                );

            byte[] bytes =
                Encoding.UTF8.GetBytes(json);

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
    }
}