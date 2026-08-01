using System;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Threading;

using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;

namespace HomeAura.AutoCAD.Agent
{
    internal static class AgentApiProcessManager
    {
        private const string AgentRoot =
            @"C:\AI\HomeAuraEngineeringAgent";

        private const string ApiAddress =
            "http://127.0.0.1:8765";

        private static readonly string PythonExecutable =
            Path.Combine(
                AgentRoot,
                ".venv",
                "Scripts",
                "python.exe"
            );

        public static bool EnsureRunning(
            out string message)
        {
            if (IsHealthy())
            {
                message =
                    "HomeAura API уже работает: " +
                    ApiAddress;

                return true;
            }

            if (!Directory.Exists(AgentRoot))
            {
                message =
                    "Не найдена папка агента: " +
                    AgentRoot;

                return false;
            }

            if (!File.Exists(PythonExecutable))
            {
                message =
                    "Не найден Python виртуального окружения: " +
                    PythonExecutable;

                return false;
            }

            try
            {
                ProcessStartInfo startInfo =
                    new ProcessStartInfo
                    {
                        FileName = PythonExecutable,

                        Arguments =
                            "-m uvicorn " +
                            "agent.api:app " +
                            "--host 127.0.0.1 " +
                            "--port 8765",

                        WorkingDirectory = AgentRoot,

                        UseShellExecute = false,
                        CreateNoWindow = true,
                        WindowStyle =
                            ProcessWindowStyle.Hidden
                    };

                startInfo.EnvironmentVariables[
                    "PYTHONUTF8"
                ] = "1";

                Process process =
                    Process.Start(startInfo);

                if (process == null)
                {
                    message =
                        "Не удалось запустить процесс API.";

                    return false;
                }

                // Ждём запуска сервера не более 8 секунд.
                for (int attempt = 0;
                     attempt < 32;
                     attempt++)
                {
                    Thread.Sleep(250);

                    if (IsHealthy())
                    {
                        message =
                            "HomeAura API автоматически запущен.";

                        return true;
                    }

                    if (process.HasExited)
                    {
                        message =
                            "Процесс API завершился сразу " +
                            "после запуска. Код: " +
                            process.ExitCode;

                        return false;
                    }
                }

                message =
                    "API запущен, но не ответил " +
                    "за отведённое время.";

                return false;
            }
            catch (System.Exception exception)
            {
                message =
                    "Ошибка запуска API: " +
                    exception.Message;

                return false;
            }
        }

        public static bool IsHealthy()
        {
            try
            {
                using (HttpClient client =
                       new HttpClient())
                {
                    client.Timeout =
                        TimeSpan.FromMilliseconds(900);

                    using (HttpResponseMessage response =
                           client
                               .GetAsync(ApiAddress + "/health")
                               .GetAwaiter()
                               .GetResult())
                    {
                        return response.IsSuccessStatusCode;
                    }
                }
            }
            catch
            {
                return false;
            }
        }

        public static string GetApiAddress()
        {
            return ApiAddress;
        }
    }

    public sealed partial class Commands
    {
        [CommandMethod(
            "HA_API_STATUS",
            CommandFlags.Modal)]
        public void ShowApiStatus()
        {
            Document document =
                Application.DocumentManager
                    .MdiActiveDocument;

            if (document == null)
            {
                return;
            }

            Editor editor = document.Editor;

            bool ready =
                AgentApiProcessManager.IsHealthy();

            editor.WriteMessage("\n");
            editor.WriteMessage(
                "\nHomeAura API: " +
                (ready
                    ? "работает"
                    : "не запущен")
            );

            editor.WriteMessage(
                "\nАдрес: " +
                AgentApiProcessManager.GetApiAddress()
            );

            editor.WriteMessage("\n");
        }

        [CommandMethod(
            "HA_API_START",
            CommandFlags.Modal)]
        public void StartApi()
        {
            Document document =
                Application.DocumentManager
                    .MdiActiveDocument;

            if (document == null)
            {
                return;
            }

            string message;

            bool ready =
                AgentApiProcessManager.EnsureRunning(
                    out message
                );

            document.Editor.WriteMessage("\n");
            document.Editor.WriteMessage(
                "\nHomeAura API: " +
                (ready ? "готов" : "ошибка")
            );

            document.Editor.WriteMessage(
                "\n" + message
            );

            document.Editor.WriteMessage("\n");
        }
    }
}
