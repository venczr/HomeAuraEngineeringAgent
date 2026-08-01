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
        [CommandMethod(
            "HA_SYNC_ROOMS",
            CommandFlags.Modal)]
        public void SyncRooms()
        {
            Document document =
                Application.DocumentManager
                    .MdiActiveDocument;

            if (document == null)
            {
                return;
            }

            Editor editor = document.Editor;

            try
            {
                string apiMessage;

                if (!AgentApiProcessManager.EnsureRunning(
                        out apiMessage))
                {
                    editor.WriteMessage(
                        "\nHomeAura API недоступен."
                    );

                    editor.WriteMessage(
                        "\n" + apiMessage
                    );

                    return;
                }

                if (string.IsNullOrWhiteSpace(
                        document.Name) ||
                    !Path.IsPathRooted(
                        document.Name))
                {
                    editor.WriteMessage(
                        "\nСначала сохрани DWG на диск."
                    );

                    return;
                }

                string drawingDirectory =
                    Path.GetDirectoryName(
                        document.Name
                    );

                if (string.IsNullOrWhiteSpace(
                        drawingDirectory))
                {
                    throw new InvalidOperationException(
                        "Не определена папка проекта."
                    );
                }

                string projectName =
                    new DirectoryInfo(
                        drawingDirectory
                    ).Name;

                RoomExportReport report =
                    ReadMagiCadRooms(document);

                string json =
                    SerializeRoomReport(report);

                string endpoint =
                    "http://127.0.0.1:8765" +
                    "/api/v1/projects/" +
                    Uri.EscapeDataString(
                        projectName
                    ) +
                    "/rooms";

                string responseText;

                using (StringContent content =
                       new StringContent(
                           json,
                           Encoding.UTF8,
                           "application/json"))
                {
                    using (HttpResponseMessage response =
                           SyncHttpClient
                               .PostAsync(
                                   endpoint,
                                   content
                               )
                               .GetAwaiter()
                               .GetResult())
                    {
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
                                "\nОтвет API: " +
                                responseText
                            );

                            return;
                        }
                    }
                }

                double totalArea = 0;
                double totalHeatLoss = 0;
                double totalSupply = 0;
                double totalExtract = 0;

                foreach (MagiCadRoom room
                         in report.Rooms)
                {
                    totalArea +=
                        room.NetAreaM2 ?? 0;

                    totalHeatLoss +=
                        room.TotalHeatLossW ?? 0;

                    totalSupply +=
                        room.SupplyAirflowM3H ?? 0;

                    totalExtract +=
                        room.ExtractAirflowM3H ?? 0;
                }

                editor.WriteMessage("\n");
                editor.WriteMessage(
                    "\n===================================="
                );
                editor.WriteMessage(
                    "\n HomeAura — синхронизация помещений"
                );
                editor.WriteMessage(
                    "\n===================================="
                );

                editor.WriteMessage(
                    "\nПроект: " + projectName
                );

                editor.WriteMessage(
                    "\nНайдено маркеров: " +
                    report.FoundMarkers
                );

                editor.WriteMessage(
                    "\nПередано помещений: " +
                    report.Rooms.Count
                );

                editor.WriteMessage(
                    "\nОбщая площадь: " +
                    FormatNumber(totalArea) +
                    " м²"
                );

                editor.WriteMessage(
                    "\nОбщие теплопотери: " +
                    FormatNumber(totalHeatLoss) +
                    " Вт"
                );

                editor.WriteMessage(
                    "\nОбщий приток: " +
                    FormatNumber(totalSupply) +
                    " м³/ч"
                );

                editor.WriteMessage(
                    "\nОбщая вытяжка: " +
                    FormatNumber(totalExtract) +
                    " м³/ч"
                );

                editor.WriteMessage(
                    "\nAPI подтвердил получение данных."
                );

                editor.WriteMessage(
                    "\n===================================="
                );
                editor.WriteMessage("\n");
            }
            catch (HttpRequestException exception)
            {
                editor.WriteMessage(
                    "\nНе удалось подключиться к API."
                );

                editor.WriteMessage(
                    "\nОшибка: " +
                    exception.Message
                );
            }
            catch (System.Exception exception)
            {
                editor.WriteMessage(
                    "\nОшибка HA_SYNC_ROOMS: " +
                    exception.Message
                );
            }
        }

        private static string SerializeRoomReport(
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

            using (MemoryStream stream =
                   new MemoryStream())
            {
                serializer.WriteObject(
                    stream,
                    report
                );

                return Encoding.UTF8.GetString(
                    stream.ToArray()
                );
            }
        }
    }
}
