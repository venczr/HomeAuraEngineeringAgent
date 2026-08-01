using System;
using System.IO;

namespace HomeAura.AutoCAD.Agent
{
    internal static class AtomicFileWriter
    {
        public static void PublishHistoryThenCurrent(
            string historyPath,
            string currentPath,
            Action<string> historyPublisher,
            Action<string> currentPublisher)
        {
            if (string.IsNullOrWhiteSpace(historyPath))
            {
                throw new ArgumentException(
                    "History path is required.",
                    "historyPath"
                );
            }

            if (string.IsNullOrWhiteSpace(currentPath))
            {
                throw new ArgumentException(
                    "Current path is required.",
                    "currentPath"
                );
            }

            if (historyPublisher == null)
            {
                throw new ArgumentNullException(
                    "historyPublisher"
                );
            }

            if (currentPublisher == null)
            {
                throw new ArgumentNullException(
                    "currentPublisher"
                );
            }

            historyPublisher(historyPath);
            currentPublisher(currentPath);
        }

        public static void Write(
            string trustedRoot,
            string path,
            Action<Stream> writer)
        {
            WriteCore(trustedRoot, path, writer, true);
        }

        public static void WriteNew(
            string trustedRoot,
            string path,
            Action<Stream> writer)
        {
            WriteCore(trustedRoot, path, writer, false);
        }

        private static void WriteCore(
            string trustedRoot,
            string path,
            Action<Stream> writer,
            bool replaceExisting)
        {
            if (string.IsNullOrWhiteSpace(trustedRoot))
            {
                throw new ArgumentException(
                    "Trusted root is required.",
                    "trustedRoot"
                );
            }

            if (string.IsNullOrWhiteSpace(path))
            {
                throw new ArgumentException(
                    "Destination path is required.",
                    "path"
                );
            }

            if (!Path.IsPathRooted(path))
            {
                throw new ArgumentException(
                    "Destination path must be absolute.",
                    "path"
                );
            }

            if (writer == null)
            {
                throw new ArgumentNullException("writer");
            }

            string destinationPath = Path.GetFullPath(path);
            string directory =
                PrepareContainedDirectory(
                    trustedRoot,
                    destinationPath,
                    ReadAttributesIfExists,
                    CreateDirectory
                );

            ValidateDestinationEntry(
                destinationPath,
                ReadAttributesIfExists
            );

            string temporaryPath = Path.Combine(
                directory,
                "." + Path.GetFileName(destinationPath) +
                "." + Guid.NewGuid().ToString("N") +
                ".tmp"
            );

            try
            {
                using (FileStream stream =
                       new FileStream(
                           temporaryPath,
                           FileMode.CreateNew,
                           FileAccess.Write,
                           FileShare.None))
                {
                    writer(stream);
                    stream.Flush(true);
                }

                PrepareContainedDirectory(
                    trustedRoot,
                    destinationPath,
                    ReadAttributesIfExists,
                    CreateDirectory
                );
                ValidateDestinationEntry(
                    destinationPath,
                    ReadAttributesIfExists
                );

                if (replaceExisting &&
                    File.Exists(destinationPath))
                {
                    File.Replace(
                        temporaryPath,
                        destinationPath,
                        null
                    );
                }
                else
                {
                    File.Move(
                        temporaryPath,
                        destinationPath
                    );
                }
            }
            finally
            {
                if (File.Exists(temporaryPath))
                {
                    File.Delete(temporaryPath);
                }
            }
        }

        internal static string PrepareContainedDirectory(
            string trustedRoot,
            string destinationPath,
            Func<string, FileAttributes?> readAttributes,
            Action<string> createDirectory)
        {
            if (string.IsNullOrWhiteSpace(trustedRoot) ||
                !Path.IsPathRooted(trustedRoot))
            {
                throw new ArgumentException(
                    "Trusted root must be an absolute path.",
                    "trustedRoot"
                );
            }

            if (string.IsNullOrWhiteSpace(destinationPath) ||
                !Path.IsPathRooted(destinationPath))
            {
                throw new ArgumentException(
                    "Destination must be an absolute path.",
                    "destinationPath"
                );
            }

            if (readAttributes == null)
            {
                throw new ArgumentNullException(
                    "readAttributes"
                );
            }

            if (createDirectory == null)
            {
                throw new ArgumentNullException(
                    "createDirectory"
                );
            }

            string rootPath = NormalizeDirectoryPath(
                trustedRoot
            );
            string fullDestinationPath =
                Path.GetFullPath(destinationPath);
            string rootPrefix = rootPath.EndsWith(
                    Path.DirectorySeparatorChar.ToString(),
                    StringComparison.Ordinal
                ) || rootPath.EndsWith(
                    Path.AltDirectorySeparatorChar.ToString(),
                    StringComparison.Ordinal
                )
                    ? rootPath
                    : rootPath + Path.DirectorySeparatorChar;

            FileAttributes? rootAttributes =
                readAttributes(rootPath);

            if (!rootAttributes.HasValue ||
                (rootAttributes.Value &
                 FileAttributes.Directory) == 0)
            {
                throw new IOException(
                    "Trusted root directory is unavailable."
                );
            }

            if (!fullDestinationPath.StartsWith(
                    rootPrefix,
                    StringComparison.OrdinalIgnoreCase))
            {
                throw new IOException(
                    "Destination escapes the trusted root."
                );
            }

            string directory =
                Path.GetDirectoryName(fullDestinationPath);

            if (string.IsNullOrWhiteSpace(directory))
            {
                throw new InvalidOperationException(
                    "Destination directory is unavailable."
                );
            }

            string relativeDirectory =
                string.Equals(
                    directory,
                    rootPath,
                    StringComparison.OrdinalIgnoreCase
                )
                    ? string.Empty
                    : directory.Substring(rootPrefix.Length);
            string current = rootPath;
            string[] components = relativeDirectory.Split(
                new[]
                {
                    Path.DirectorySeparatorChar,
                    Path.AltDirectorySeparatorChar
                },
                StringSplitOptions.RemoveEmptyEntries
            );

            for (int index = 0;
                 index < components.Length;
                 index++)
            {
                current = Path.Combine(
                    current,
                    components[index]
                );

                FileAttributes? attributes =
                    readAttributes(current);

                if (!attributes.HasValue)
                {
                    createDirectory(current);
                    attributes = readAttributes(current);
                }

                ValidateDirectoryEntry(
                    attributes
                );
            }

            ValidateDestinationEntry(
                fullDestinationPath,
                readAttributes
            );

            return directory;
        }

        private static string NormalizeDirectoryPath(
            string path)
        {
            string fullPath = Path.GetFullPath(path);
            string pathRoot = Path.GetPathRoot(fullPath);

            if (!string.Equals(
                    fullPath,
                    pathRoot,
                    StringComparison.OrdinalIgnoreCase))
            {
                fullPath = fullPath.TrimEnd(
                    Path.DirectorySeparatorChar,
                    Path.AltDirectorySeparatorChar
                );
            }

            return fullPath;
        }

        private static void ValidateDirectoryEntry(
            FileAttributes? attributes)
        {
            if (!attributes.HasValue ||
                (attributes.Value & FileAttributes.Directory) == 0)
            {
                throw new IOException(
                    "Output directory is unavailable."
                );
            }

            if ((attributes.Value &
                 FileAttributes.ReparsePoint) != 0)
            {
                throw new IOException(
                    "Output directory cannot be a reparse point."
                );
            }
        }

        private static void ValidateDestinationEntry(
            string path,
            Func<string, FileAttributes?> readAttributes)
        {
            FileAttributes? attributes = readAttributes(path);

            if (!attributes.HasValue)
            {
                return;
            }

            if ((attributes.Value &
                 FileAttributes.ReparsePoint) != 0)
            {
                throw new IOException(
                    "Output file cannot be a reparse point."
                );
            }

            if ((attributes.Value & FileAttributes.Directory) != 0)
            {
                throw new IOException(
                    "Output destination cannot be a directory."
                );
            }
        }

        private static FileAttributes? ReadAttributesIfExists(
            string path)
        {
            try
            {
                return File.GetAttributes(path);
            }
            catch (FileNotFoundException)
            {
                return null;
            }
            catch (DirectoryNotFoundException)
            {
                return null;
            }
        }

        private static void CreateDirectory(string path)
        {
            Directory.CreateDirectory(path);
        }
    }
}
