using System;
using System.IO;
using System.Text;

using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;

namespace HomeAura.AutoCAD.Agent
{
    public sealed partial class Commands
    {
        private const string FloorHeatingRuntimeRoot =
            @"C:\AI\HomeAuraRuntime\cad_tests";

        [CommandMethod(
            "HA_FLOOR_HEATING",
            CommandFlags.Modal)]
        public void RenderFloorHeating()
        {
            Document document =
                Application.DocumentManager.MdiActiveDocument;
            if (document == null) return;

            Editor editor = document.Editor;
            try
            {
                PromptResult payloadPrompt = editor.GetString(
                    new PromptStringOptions(
                        "\nStrict floor-heating preview JSON path: "
                    )
                    {
                        AllowSpaces = true
                    }
                );
                if (payloadPrompt.Status != PromptStatus.OK)
                {
                    return;
                }

                PromptResult outputPrompt = editor.GetString(
                    new PromptStringOptions(
                        "\nDisposable output DWG path: "
                    )
                    {
                        AllowSpaces = true
                    }
                );
                if (outputPrompt.Status != PromptStatus.OK)
                {
                    return;
                }

                string payloadPath = payloadPrompt.StringResult.Trim();
                string outputPath = outputPrompt.StringResult.Trim();
                Directory.CreateDirectory(FloorHeatingRuntimeRoot);
                ValidateOutputPath(outputPath, FloorHeatingRuntimeRoot);

                FloorHeatingPayloadData payload =
                    FloorHeatingPayloadReader.Load(
                        payloadPath,
                        FloorHeatingRuntimeRoot
                    );

                bool existing = File.Exists(outputPath);
                FloorHeatingRenderResult renderResult;
                bool activeTarget =
                    !string.IsNullOrWhiteSpace(document.Name) &&
                    Path.IsPathRooted(document.Name) &&
                    string.Equals(
                        Path.GetFullPath(document.Name),
                        Path.GetFullPath(outputPath),
                        StringComparison.OrdinalIgnoreCase
                    );

                if (activeTarget)
                {
                    renderResult = FloorHeatingRenderer.Apply(
                        document.Database,
                        payload
                    );
                }
                else
                {
                    using (Database database = new Database(!existing, true))
                    {
                        if (existing)
                        {
                            database.ReadDwgFile(
                                outputPath,
                                FileOpenMode.OpenForReadAndAllShare,
                                false,
                                ""
                            );
                        }
                        else
                        {
                            database.Insunits = UnitsValue.Millimeters;
                        }

                        renderResult = FloorHeatingRenderer.Apply(
                            database,
                            payload
                        );
                        database.SaveAs(outputPath, DwgVersion.Current);
                    }
                }

                editor.WriteMessage("\n");
                editor.WriteMessage(
                    "\nHomeAura floor-heating disposable drawing ready."
                );
                editor.WriteMessage(
                    "\nDWG: " +
                    AutoCadDisplayText.Format(
                        outputPath,
                        AutoCadDisplayText.PathLimit
                    )
                );
                editor.WriteMessage(
                    "\nProject/room: " + payload.ProjectId + "/" +
                    payload.RoomId
                );
                editor.WriteMessage(
                    "\nCircuits: " + payload.Circuits.Count +
                    "; collector ports: " + payload.CollectorPortCount
                );
                editor.WriteMessage(
                    "\nGeometry entities: " +
                    renderResult.CircuitGeometryCount
                );
                editor.WriteMessage(
                    "\nIdempotent no-op: " + renderResult.NoOp
                );
            }
            catch (FloorHeatingPayloadException exception)
            {
                editor.WriteMessage(
                    "\nHomeAura floor-heating payload rejected: " +
                    SafeMessage(exception.Message)
                );
            }
            catch (System.Exception exception)
            {
                editor.WriteMessage(
                    AutoCadCommandDiagnostics.FormatUnexpected(
                        AutoCadCommandOperation.ExportRooms
                    )
                );
                editor.WriteMessage(
                    "\nFloor-heating safe error type: " +
                    exception.GetType().Name
                );
                editor.WriteMessage(
                    "\nFloor-heating safe error: " +
                    SafeMessage(exception.Message)
                );
            }
        }

        private static void ValidateOutputPath(
            string outputPath,
            string trustedRoot)
        {
            if (string.IsNullOrWhiteSpace(outputPath) ||
                !Path.IsPathRooted(outputPath))
            {
                throw new FloorHeatingPayloadException(
                    "Output DWG path must be absolute."
                );
            }

            string root = Path.GetFullPath(trustedRoot)
                .TrimEnd(Path.DirectorySeparatorChar) +
                Path.DirectorySeparatorChar;
            string full = Path.GetFullPath(outputPath);
            if (!full.StartsWith(root, StringComparison.OrdinalIgnoreCase) ||
                !string.Equals(
                    Path.GetExtension(full),
                    ".dwg",
                    StringComparison.OrdinalIgnoreCase
                ))
            {
                throw new FloorHeatingPayloadException(
          "Output DWG must remain inside the disposable CAD runtime root."
                );
            }
        }

        private static string SafeMessage(string value)
        {
            if (string.IsNullOrWhiteSpace(value)) return "Invalid payload.";
            string normalized = value.Replace("\r", " ").Replace("\n", " ");
            return normalized.Length <= 400
                ? normalized
                : normalized.Substring(0, 400);
        }
    }
}
