using System;
using System.IO;
using System.Net.Http;
using System.Runtime.Serialization.Json;
using System.Text;

using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;

namespace HomeAura.AutoCAD.Agent
{
    public sealed partial class Commands
    {
        private static readonly HttpClient SyncHttpClient =
            CreateSyncHttpClient();

        [CommandMethod("HA_SYNC_MODEL", CommandFlags.Modal)]
        public void SyncModel()
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

                string apiMessage;

                if (!AgentApiProcessManager.EnsureRunning(
                        out apiMessage))
                {
                    editor.WriteMessage(
                        "\nHomeAura API недоступен."
                    );
                    editor.WriteMessage("\n" + apiMessage);
                    return;
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
                    "/snapshot";

                using (StringContent content =
                       new StringContent(
                           json,
                           Encoding.UTF8,
                           "application/json"))
                {
                    using (HttpResponseMessage response =
                           SyncHttpClient
                               .PostAsync(endpoint, content)
                               .GetAwaiter()
                               .GetResult())
                    {
                        if (!response.IsSuccessStatusCode)
                        {
                            editor.WriteMessage(
                                "\n" +
                                ApiResponseDiagnostics
                                    .FormatFailure(
                                        response.StatusCode
                                    )
                            );

                            return;
                        }
                    }
                }

                editor.WriteMessage("\n");
                editor.WriteMessage(
                    "\nHomeAura: модель синхронизирована."
                );
                editor.WriteMessage(
                    "\nПроект: " + projectName
                );
                editor.WriteMessage(
                    "\nЧертёж: " + snapshot.DrawingName
                );
                editor.WriteMessage(
                    "\nОбъектов: " +
                    snapshot.ModelSpaceEntityCount
                );
                editor.WriteMessage(
                    "\nСлоёв: " +
                    snapshot.Layers.Count
                );
                editor.WriteMessage(
                    "\nТипов объектов: " +
                    snapshot.EntityTypes.Count
                );
                editor.WriteMessage(
                    "\nAPI: " + endpoint
                );
                editor.WriteMessage("\n");
            }
            catch (System.Threading.Tasks.TaskCanceledException exception)
            {
                editor.WriteMessage(
                    "\n" +
                    ApiResponseDiagnostics
                        .FormatTransportFailure(exception)
                );
            }
            catch (HttpRequestException exception)
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
            catch (System.Exception exception)
            {
                editor.WriteMessage(
                    "\nОшибка HA_SYNC_MODEL: " +
                    exception.Message
                );
            }
        }

        private static HttpClient CreateSyncHttpClient()
        {
            return new HttpClient
            {
                Timeout = TimeSpan.FromSeconds(15)
            };
        }

        private static string SerializeSnapshot(
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

            using (MemoryStream stream =
                   new MemoryStream())
            {
                serializer.WriteObject(
                    stream,
                    snapshot
                );

                return Encoding.UTF8.GetString(
                    stream.ToArray()
                );
            }
        }
    }
}
