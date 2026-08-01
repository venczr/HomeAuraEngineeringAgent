using System;
using System.Globalization;
using System.IO;
using System.Security;

namespace HomeAura.AutoCAD.Agent
{
    internal enum AgentApiStartupFailure
    {
        AgentRootMissing,
        PythonMissing,
        ProcessStartFailed,
        ProcessExited,
        ReadinessTimeout,
        Unexpected
    }

    internal static class AgentApiStartupPolicy
    {
        internal const string AgentRootEnvironmentVariable =
            "HOMEAURA_AGENT_ROOT";

        public static string ResolveAgentRoot(
            string configuredRoot,
            string assemblyDirectory)
        {
            if (configuredRoot != null)
            {
                return TryResolveExplicitRoot(configuredRoot);
            }

            if (string.IsNullOrWhiteSpace(assemblyDirectory))
            {
                return null;
            }

            try
            {
                DirectoryInfo current =
                    new DirectoryInfo(
                        Path.GetFullPath(assemblyDirectory)
                    );

                while (current != null)
                {
                    if (IsAgentRoot(current.FullName))
                    {
                        return current.FullName;
                    }

                    current = current.Parent;
                }
            }
            catch (ArgumentException)
            {
                return null;
            }
            catch (IOException)
            {
                return null;
            }
            catch (NotSupportedException)
            {
                return null;
            }
            catch (SecurityException)
            {
                return null;
            }
            catch (UnauthorizedAccessException)
            {
                return null;
            }

            return null;
        }

        public static string GetPythonExecutable(
            string agentRoot)
        {
            if (string.IsNullOrWhiteSpace(agentRoot))
            {
                throw new ArgumentException(
                    "Agent root is required.",
                    "agentRoot"
                );
            }

            return Path.Combine(
                agentRoot,
                ".venv",
                "Scripts",
                "python.exe"
            );
        }

        public static string FormatFailure(
            AgentApiStartupFailure failure,
            int? exitCode)
        {
            if (failure == AgentApiStartupFailure.ProcessExited)
            {
                if (!exitCode.HasValue)
                {
                    throw new ArgumentException(
                        "Process exit code is required.",
                        "exitCode"
                    );
                }

                return
                    "Процесс HomeAura API завершился при запуске " +
                    "(код " +
                    exitCode.Value.ToString(
                        CultureInfo.InvariantCulture) +
                    ").";
            }

            if (exitCode.HasValue)
            {
                throw new ArgumentException(
                    "Exit code is only valid for ProcessExited.",
                    "exitCode"
                );
            }

            switch (failure)
            {
                case AgentApiStartupFailure.AgentRootMissing:
                    return
                        "Не найдена папка HomeAura Agent. " +
                        "Задайте HOMEAURA_AGENT_ROOT.";

                case AgentApiStartupFailure.PythonMissing:
                    return
                        "Не найден Python HomeAura " +
                        "(.venv\\Scripts\\python.exe). " +
                        "Создайте окружение по lock-файлам проекта.";

                case AgentApiStartupFailure.ProcessStartFailed:
                    return
                        "Не удалось запустить локальный процесс " +
                        "HomeAura API.";

                case AgentApiStartupFailure.ReadinessTimeout:
                    return
                        "HomeAura API запущен, но не ответил " +
                        "за 8 секунд.";

                case AgentApiStartupFailure.Unexpected:
                    return
                        "Не удалось запустить HomeAura API " +
                        "из-за локальной ошибки.";

                default:
                    throw new ArgumentOutOfRangeException(
                        "failure"
                    );
            }
        }

        private static string TryResolveExplicitRoot(
            string configuredRoot)
        {
            try
            {
                if (string.IsNullOrWhiteSpace(configuredRoot) ||
                    !Path.IsPathRooted(configuredRoot))
                {
                    return null;
                }

                string fullPath =
                    Path.GetFullPath(configuredRoot);

                return IsAgentRoot(fullPath)
                    ? fullPath
                    : null;
            }
            catch (ArgumentException)
            {
                return null;
            }
            catch (IOException)
            {
                return null;
            }
            catch (NotSupportedException)
            {
                return null;
            }
            catch (SecurityException)
            {
                return null;
            }
            catch (UnauthorizedAccessException)
            {
                return null;
            }
        }

        private static bool IsAgentRoot(string path)
        {
            return
                Directory.Exists(path) &&
                File.Exists(
                    Path.Combine(path, "agent", "api.py")
                );
        }
    }

    internal sealed class AgentApiStartupException : Exception
    {
        public AgentApiStartupException(string safeMessage)
            : base(ValidateMessage(safeMessage))
        {
            SafeMessage = Message;
        }

        public string SafeMessage { get; private set; }

        private static string ValidateMessage(
            string safeMessage)
        {
            if (string.IsNullOrWhiteSpace(safeMessage) ||
                safeMessage.Length > 256)
            {
                throw new ArgumentException(
                    "A bounded startup message is required.",
                    "safeMessage"
                );
            }

            return safeMessage;
        }
    }
}
