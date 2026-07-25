using System;
using System.IO;
using System.Reflection;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;

[assembly: ExtensionApplication(typeof(HomeAura.AutoCAD.Agent.Plugin))]
[assembly: CommandClass(typeof(HomeAura.AutoCAD.Agent.Commands))]

namespace HomeAura.AutoCAD.Agent
{
    public sealed class Plugin : IExtensionApplication
    {
        public void Initialize()
        {
            Document document =
                Application.DocumentManager.MdiActiveDocument;

            if (document == null)
            {
                return;
            }

            document.Editor.WriteMessage(
                "\nHomeAura AutoCAD Agent загружен." +
                "\nВведите команду HA_STATUS для проверки."
            );
        }

        public void Terminate()
        {
            // Освобождение ресурсов добавим позже.
        }
    }

    public sealed class Commands
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
            editor.WriteMessage(
                $"\nПлагин загружен: Да"
            );
            editor.WriteMessage(
                $"\nВерсия плагина: {pluginVersion}"
            );
            editor.WriteMessage(
                $"\nAutoCAD ACADVER: {acadVersion}"
            );
            editor.WriteMessage(
                $"\n64-битный процесс: {Environment.Is64BitProcess}"
            );
            editor.WriteMessage(
                $"\nТекущий чертёж: {drawingName}"
            );
            editor.WriteMessage("\n====================================");
            editor.WriteMessage("\n");
        }
    }
}