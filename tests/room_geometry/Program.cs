using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;

using HomeAura.AutoCAD.Agent;

namespace HomeAura.AutoCAD.Agent.Tests
{
    internal static class Program
    {
        private static int passed;

        private static int Main()
        {
            try
            {
                Run(
                    "simple rectangle",
                    TestSimpleRectangle
                );
                Run(
                    "reverse vertex direction",
                    TestReverseDirection
                );
                Run(
                    "duplicate vertices",
                    TestDuplicateVertices
                );
                Run(
                    "self intersection",
                    TestSelfIntersection
                );
                Run(
                    "arc segment",
                    TestArcSegment
                );
                Run(
                    "nested contours",
                    TestNestedContours
                );
                Run(
                    "millimeters and meters",
                    TestDrawingUnits
                );
                Run(
                    "MagiCAD area difference",
                    TestAreaDifference
                );
                Run(
                    "Polyline3d Closed flag",
                    TestPolyline3dClosedFlag
                );
                Run(
                    "Polyline3d repeated closure",
                    TestPolyline3dRepeatedClosure
                );
                Run(
                    "Polyline3d open",
                    TestPolyline3dOpen
                );
                Run(
                    "Polyline3d non-planar",
                    TestPolyline3dNonPlanar
                );
                Run(
                    "Polyline3d duplicate vertices",
                    TestPolyline3dDuplicates
                );
                Run(
                    "Polyline3d non-finite vertex",
                    TestPolyline3dNonFiniteVertex
                );
                Run(
                    "Polyline3d null vertex",
                    TestPolyline3dNullVertex
                );
                Run(
                    "Polyline3d non-finite units",
                    TestPolyline3dNonFiniteUnits
                );
                Run(
                    "Polyline3d metric overflow",
                    TestPolyline3dMetricOverflow
                );
                Run(
                    "engineering non-finite numeric",
                    TestEngineeringNonFiniteNumeric
                );
                Run(
                    "snapshot overflow-safe midpoint",
                    TestSnapshotOverflowSafeMidpoint
                );
                Run(
                    "MagiCAD finite single decoding",
                    TestMagiCadFiniteSingleDecoding
                );
                Run(
                    "engineering scaled span",
                    TestEngineeringScaledSpan
                );
                Run(
                    "API response diagnostics",
                    TestApiResponseDiagnostics
                );
                Run(
                    "AutoCAD command diagnostics",
                    TestAutoCadCommandDiagnostics
                );
                Run(
                    "AutoCAD safe user diagnostics",
                    TestAutoCadSafeUserDiagnostics
                );
                Run(
                    "API startup root policy",
                    TestAgentApiStartupRootPolicy
                );
                Run(
                    "API startup diagnostics",
                    TestAgentApiStartupDiagnostics
                );
                Run(
                    "remote Handle selection plan",
                    TestRemoteHandleSelectionPlan
                );
                Run(
                    "remote Handle selection validation",
                    TestRemoteHandleSelectionValidation
                );
                Run(
                    "atomic writer publishes complete file",
                    TestAtomicWriterPublishesCompleteFile
                );
                Run(
                    "atomic writer preserves destination",
                    TestAtomicWriterPreservesDestination
                );
                Run(
                    "atomic create-only preserves destination",
                    TestAtomicWriterCreateOnlyPreservesDestination
                );
                Run(
                    "history-first publication order",
                    TestHistoryFirstPublicationOrder
                );
                Run(
                    "history failure preserves current",
                    TestHistoryFailurePreservesCurrent
                );
                Run(
                    "Polyline3d self intersection",
                    TestPolyline3dSelfIntersection
                );
                Run(
                    "Polyline3d marker outside",
                    TestPolyline3dMarkerOutside
                );
                Run(
                    "MagiCAD boundary priority",
                    TestMagiCadBoundaryPriority
                );
                Run(
                    "area mismatch warning over 15 percent",
                    TestAreaMismatchWarning
                );

                Console.WriteLine(
                    "PASS: " + passed +
                    " room geometry tests"
                );

                return 0;
            }
            catch (System.Exception exception)
            {
                Console.Error.WriteLine(
                    "FAIL: " + exception.Message
                );

                return 1;
            }
        }

        private static void TestSimpleRectangle()
        {
            List<RoomBoundaryVertex> vertices =
                Rectangle(0, 0, 4, 3);

            int removed;

            List<RoomBoundaryVertex> normalized =
                RoomGeometryMath.NormalizeVertices(
                    vertices,
                    1e-9,
                    true,
                    out removed
                );

            AssertEqual(0, removed, "removed");
            AssertEqual(
                4,
                normalized.Count,
                "vertex count"
            );
            AssertNear(
                12,
                RoomGeometryMath.CalculateSignedArea(
                    normalized
                ),
                1e-9,
                "area"
            );
            AssertEqual(
                "CCW",
                RoomGeometryMath.GetDirection(
                    normalized
                ),
                "direction"
            );
            AssertFalse(
                RoomGeometryMath
                    .HasSelfIntersections(
                        normalized,
                        0.01,
                        1e-9
                    ),
                "rectangle self-intersects"
            );

            RoomBoundary boundary =
                ValidBoundary(normalized, 12);

            AssertTrue(
                RoomGeometryMath.ContainsPoint(
                    boundary,
                    2,
                    1
                ),
                "point must be inside"
            );
            AssertFalse(
                RoomGeometryMath.ContainsPoint(
                    boundary,
                    5,
                    1
                ),
                "point must be outside"
            );
        }

        private static void TestReverseDirection()
        {
            List<RoomBoundaryVertex> clockwise =
                new List<RoomBoundaryVertex>
                {
                    Vertex(0, 0),
                    Vertex(0, 3),
                    Vertex(4, 3),
                    Vertex(4, 0)
                };

            AssertEqual(
                "CW",
                RoomGeometryMath.GetDirection(
                    clockwise
                ),
                "original direction"
            );

            List<RoomBoundaryVertex> normalized =
                RoomGeometryMath
                    .NormalizeCounterClockwise(
                        clockwise
                    );

            AssertEqual(
                "CCW",
                RoomGeometryMath.GetDirection(
                    normalized
                ),
                "normalized direction"
            );
            AssertNear(
                12,
                RoomGeometryMath.CalculateSignedArea(
                    normalized
                ),
                1e-9,
                "normalized area"
            );
        }

        private static void TestDuplicateVertices()
        {
            List<RoomBoundaryVertex> source =
                new List<RoomBoundaryVertex>
                {
                    Vertex(0, 0),
                    Vertex(4, 0),
                    Vertex(4, 0),
                    Vertex(4, 3),
                    Vertex(0, 3),
                    Vertex(0, 0)
                };

            int removed;

            List<RoomBoundaryVertex> normalized =
                RoomGeometryMath.NormalizeVertices(
                    source,
                    1e-8,
                    true,
                    out removed
                );

            AssertEqual(
                2,
                removed,
                "duplicate count"
            );
            AssertEqual(
                4,
                normalized.Count,
                "logical closure vertex count"
            );
        }

        private static void TestSelfIntersection()
        {
            List<RoomBoundaryVertex> bowTie =
                new List<RoomBoundaryVertex>
                {
                    Vertex(0, 0),
                    Vertex(4, 4),
                    Vertex(0, 4),
                    Vertex(4, 0)
                };

            AssertTrue(
                RoomGeometryMath
                    .HasSelfIntersections(
                        bowTie,
                        0.01,
                        1e-9
                    ),
                "bow-tie must self-intersect"
            );
        }

        private static void TestArcSegment()
        {
            List<RoomBoundaryVertex> vertices =
                new List<RoomBoundaryVertex>
                {
                    Vertex(0, 0, 1),
                    Vertex(2, 0),
                    Vertex(2, 2),
                    Vertex(0, 2)
                };

            double expectedArea =
                4 + Math.PI / 2;

            AssertNear(
                expectedArea,
                RoomGeometryMath.CalculateSignedArea(
                    vertices
                ),
                1e-9,
                "arc signed area"
            );

            List<RoomBoundaryVertex> flattened =
                RoomGeometryMath.Flatten(
                    vertices,
                    0.01
                );

            AssertTrue(
                flattened.Count > 5,
                "arc must be discretized"
            );

            RoomBoundary boundary =
                ValidBoundary(
                    vertices,
                    expectedArea
                );

            boundary.Diagnostics
                .ArcChordToleranceDrawingUnits = 0.01;

            AssertTrue(
                RoomGeometryMath.ContainsPoint(
                    boundary,
                    1,
                    1
                ),
                "point inside arc contour"
            );
        }

        private static void TestNestedContours()
        {
            RoomBoundary outer =
                ValidBoundary(
                    Rectangle(0, 0, 10, 10),
                    100
                );

            outer.SourceHandle = "OUTER";

            RoomBoundary inner =
                ValidBoundary(
                    Rectangle(4, 4, 6, 6),
                    4
                );

            inner.SourceHandle = "INNER";

            int containingCount;

            RoomBoundary selected =
                RoomGeometryMath
                    .SelectSmallestContaining(
                        new List<RoomBoundary>
                        {
                            outer,
                            inner
                        },
                        5,
                        5,
                        out containingCount
                    );

            AssertEqual(
                2,
                containingCount,
                "containing count"
            );
            AssertEqual(
                "INNER",
                selected.SourceHandle,
                "selected handle"
            );
        }

        private static void TestDrawingUnits()
        {
            double millimeters;
            double meters;

            AssertTrue(
                RoomGeometryMath
                    .TryGetMetersPerDrawingUnit(
                        "Millimeters",
                        out millimeters
                    ),
                "millimeters recognized"
            );

            AssertTrue(
                RoomGeometryMath
                    .TryGetMetersPerDrawingUnit(
                        "Meters",
                        out meters
                    ),
                "meters recognized"
            );

            AssertNear(
                0.001,
                millimeters,
                1e-12,
                "millimeter factor"
            );
            AssertNear(
                1,
                meters,
                1e-12,
                "meter factor"
            );
        }

        private static void TestAreaDifference()
        {
            RoomBoundary boundary =
                ValidBoundary(
                    Rectangle(0, 0, 5, 4),
                    20
                );

            AssertNear(
                3,
                RoomGeometryMath
                    .CalculateAreaDifferenceM2(
                        17,
                        boundary
                    ).Value,
                1e-9,
                "area difference"
            );

            AssertNear(
                17.6470588235,
                RoomGeometryMath
                    .CalculateAreaDifferencePercent(
                        17,
                        boundary
                    ).Value,
                1e-9,
                "area difference percent"
            );
        }

        private static void TestPolyline3dClosedFlag()
        {
            RoomBoundary boundary =
                Polyline3dBoundary(
                    Rectangle(0, 0, 4, 3),
                    true
                );

            AssertTrue(
                boundary.Diagnostics.IsValid,
                "closed Polyline3d must be valid"
            );
            AssertTrue(
                boundary.OriginalClosedFlag,
                "original Closed flag"
            );
            AssertEqual(
                "AutoCAD Closed flag",
                boundary.LogicalClosureMethod,
                "closure method"
            );
            AssertNear(
                12,
                boundary.ContourAreaM2.Value,
                1e-9,
                "Polyline3d area"
            );
            AssertNear(
                14,
                boundary.PerimeterM.Value,
                1e-9,
                "Polyline3d perimeter"
            );
        }

        private static void TestPolyline3dRepeatedClosure()
        {
            List<RoomBoundaryVertex> source =
                Rectangle(0, 0, 4, 3);

            source.Add(Vertex(0, 0));

            RoomBoundary boundary =
                Polyline3dBoundary(source, false);

            AssertTrue(
                boundary.Diagnostics.IsValid,
                "repeated closure must be valid"
            );
            AssertEqual(
                "Repeated first/last vertex",
                boundary.LogicalClosureMethod,
                "closure method"
            );
            AssertEqual(
                5,
                boundary.SourceVertices.Count,
                "all source XYZ must be retained"
            );
            AssertEqual(
                4,
                boundary.Vertices.Count,
                "logical closure must be normalized"
            );
        }

        private static void TestPolyline3dOpen()
        {
            RoomBoundary boundary =
                Polyline3dBoundary(
                    Rectangle(0, 0, 4, 3),
                    false
                );

            AssertFalse(
                boundary.Diagnostics.IsValid,
                "open Polyline3d must be rejected"
            );
            AssertEqual(
                "Open",
                boundary.LogicalClosureMethod,
                "open closure method"
            );
        }

        private static void TestPolyline3dNonPlanar()
        {
            List<RoomBoundaryVertex> source =
                Rectangle(0, 0, 4, 3);

            source[2].Z = 0.0011;

            RoomBoundary boundary =
                Polyline3dBoundary(source, true);

            AssertFalse(
                boundary.Diagnostics.IsValid,
                "more than 1 mm Z deviation must fail"
            );
            AssertFalse(
                boundary.IsPlanar,
                "non-planar flag"
            );
            AssertNear(
                0.0011,
                boundary.ZDeviationM.Value,
                1e-12,
                "Z deviation"
            );
        }

        private static void TestPolyline3dDuplicates()
        {
            List<RoomBoundaryVertex> source =
                new List<RoomBoundaryVertex>
                {
                    Vertex(0, 0),
                    Vertex(4, 0),
                    Vertex(4, 0),
                    Vertex(4, 3),
                    Vertex(0, 3)
                };

            RoomBoundary boundary =
                Polyline3dBoundary(source, true);

            AssertTrue(
                boundary.Diagnostics.IsValid,
                "duplicates must be normalized"
            );
            AssertEqual(
                1,
                boundary.Diagnostics
                    .DuplicateVerticesRemoved,
                "removed duplicate count"
            );
        }

        private static void TestEngineeringNonFiniteNumeric()
        {
            double[] values =
            {
                double.NaN,
                double.PositiveInfinity,
                double.NegativeInfinity
            };

            foreach (double value in values)
            {
                bool rejected = false;
                try
                {
                    EngineeringNumericGuard.RequireFinite(
                        value,
                        "Extents.Minimum.X"
                    );
                }
                catch (InvalidOperationException exception)
                {
                    rejected = exception.Message.Contains(
                        "Extents.Minimum.X"
                    );
                }

                AssertTrue(
                    rejected,
                    "non-finite snapshot coordinate must fail closed"
                );
            }
        }

        private static void TestSnapshotOverflowSafeMidpoint()
        {
            double equalExtreme =
                EngineeringNumericGuard.Midpoint(
                    double.MaxValue,
                    double.MaxValue,
                    "Entity.Center.X"
                );
            AssertEqual(
                double.MaxValue,
                equalExtreme,
                "equal extreme midpoint"
            );

            double oppositeExtreme =
                EngineeringNumericGuard.Midpoint(
                    -double.MaxValue,
                    double.MaxValue,
                    "Entity.Center.Y"
                );
            AssertEqual(
                0.0,
                oppositeExtreme,
                "opposite extreme midpoint"
            );

            AssertEqual(
                2.0,
                EngineeringNumericGuard.Midpoint(
                    1.0,
                    3.0,
                    "Entity.Center.Z"
                ),
                "ordinary midpoint"
            );
        }

        private static void TestMagiCadFiniteSingleDecoding()
        {
            AssertEqual(
                42.5,
                EngineeringNumericGuard.ReadFiniteSingle(
                    BitConverter.GetBytes((float)42.5),
                    "MagiCAD field 0x051D"
                ),
                "finite MagiCAD single"
            );

            float[] values =
            {
                float.NaN,
                float.PositiveInfinity,
                float.NegativeInfinity
            };

            foreach (float value in values)
            {
                bool rejected = false;
                try
                {
                    EngineeringNumericGuard.ReadFiniteSingle(
                        BitConverter.GetBytes(value),
                        "MagiCAD field 0x051D"
                    );
                }
                catch (InvalidOperationException exception)
                {
                    rejected = exception.Message.Contains(
                        "MagiCAD field 0x051D"
                    );
                }

                AssertTrue(
                    rejected,
                    "non-finite MagiCAD single must fail closed"
                );
            }
        }

        private static void TestEngineeringScaledSpan()
        {
            AssertEqual(
                6.0,
                EngineeringNumericGuard.ScaledSpan(
                    0.0,
                    4.0,
                    1.0,
                    1.5,
                    "Width"
                ),
                "ordinary scaled span"
            );
            AssertEqual(
                6.0,
                EngineeringNumericGuard.ScaledSpan(
                    4.0,
                    0.0,
                    1.0,
                    1.5,
                    "Width"
                ),
                "reversed scaled span"
            );
            AssertEqual(
                1500.0,
                EngineeringNumericGuard.ScaledSpan(
                    1.0,
                    2.0,
                    1000.0,
                    1.5,
                    "Width"
                ),
                "minimum scaled span"
            );

            bool spanOverflowRejected = false;
            try
            {
                EngineeringNumericGuard.ScaledSpan(
                    -double.MaxValue,
                    double.MaxValue,
                    1.0,
                    1.0,
                    "Width"
                );
            }
            catch (InvalidOperationException)
            {
                spanOverflowRejected = true;
            }
            AssertTrue(
                spanOverflowRejected,
                "span overflow must fail closed"
            );

            bool scaleOverflowRejected = false;
            try
            {
                EngineeringNumericGuard.ScaledSpan(
                    0.0,
                    double.MaxValue,
                    1.0,
                    1.5,
                    "Width"
                );
            }
            catch (InvalidOperationException)
            {
                scaleOverflowRejected = true;
            }
            AssertTrue(
                scaleOverflowRejected,
                "scale overflow must fail closed"
            );

            foreach (double value in new[] { 0.0, -1.0 })
            {
                bool rejected = false;
                try
                {
                    EngineeringNumericGuard
                        .RequirePositiveFinite(
                            value,
                            "View.Width"
                        );
                }
                catch (InvalidOperationException)
                {
                    rejected = true;
                }
                AssertTrue(
                    rejected,
                    "non-positive value must fail closed"
                );
            }
        }

        private static void TestAtomicWriterPublishesCompleteFile()
        {
            string directory = CreateTestDirectory();
            string destination =
                Path.Combine(directory, "report.json");

            try
            {
                WriteAtomicText(destination, "first");
                AssertEqual(
                    "first",
                    File.ReadAllText(destination),
                    "new atomic file"
                );

                WriteAtomicText(destination, "replacement");
                AssertEqual(
                    "replacement",
                    File.ReadAllText(destination),
                    "atomic replacement"
                );
                AssertNoAtomicTemporaryFiles(
                    directory,
                    destination
                );
            }
            finally
            {
                Directory.Delete(directory, true);
            }
        }

        private static void TestApiResponseDiagnostics()
        {
            string timeout =
                ApiResponseDiagnostics.FormatTransportFailure(
                    new TaskCanceledException(
                        "Bearer private-timeout-token"
                    )
                );
            AssertEqual(
                "HomeAura API не ответил за 15 секунд.",
                timeout,
                "timeout diagnostic"
            );
            AssertTrue(
                timeout.IndexOf(
                    "private-timeout-token",
                    StringComparison.Ordinal
                ) < 0,
                "timeout diagnostic must hide exception message"
            );

            string connection =
                ApiResponseDiagnostics.FormatTransportFailure(
                    new HttpRequestException(
                        "C:\\private\\socket"
                    )
                );
            AssertEqual(
                "Не удалось подключиться к HomeAura API.",
                connection,
                "connection diagnostic"
            );
            AssertTrue(
                connection.IndexOf(
                    "C:\\private\\socket",
                    StringComparison.Ordinal
                ) < 0,
                "connection diagnostic must hide exception message"
            );

            AssertEqual(
                "Ошибка локального запроса к HomeAura API.",
                ApiResponseDiagnostics.FormatTransportFailure(
                    new InvalidOperationException("private")
                ),
                "generic transport diagnostic"
            );

            bool nullRejected = false;
            try
            {
                ApiResponseDiagnostics.FormatTransportFailure(
                    null
                );
            }
            catch (ArgumentNullException)
            {
                nullRejected = true;
            }
            AssertTrue(
                nullRejected,
                "null transport exception must be rejected"
            );

            AssertEqual(
                "HomeAura API вернул ошибку 401 Unauthorized. " +
                "Диагностическое тело ответа скрыто.",
                ApiResponseDiagnostics.FormatFailure(
                    HttpStatusCode.Unauthorized
                ),
                "401 diagnostic"
            );
            AssertEqual(
                "HomeAura API вернул ошибку 403 Forbidden. " +
                "Диагностическое тело ответа скрыто.",
                ApiResponseDiagnostics.FormatFailure(
                    HttpStatusCode.Forbidden
                ),
                "403 diagnostic"
            );
            AssertEqual(
                "HomeAura API вернул ошибку 429 TooManyRequests. " +
                "Диагностическое тело ответа скрыто.",
                ApiResponseDiagnostics.FormatFailure(
                    (HttpStatusCode)429
                ),
                "429 diagnostic"
            );
            AssertEqual(
                "HomeAura API вернул ошибку 422 " +
                "UnprocessableEntity. " +
                "Диагностическое тело ответа скрыто.",
                ApiResponseDiagnostics.FormatFailure(
                    (HttpStatusCode)422
                ),
                "422 diagnostic"
            );

            string unknown =
                ApiResponseDiagnostics.FormatFailure(
                    (HttpStatusCode)599
                );
            AssertEqual(
                "HomeAura API вернул ошибку 599 UnknownStatus. " +
                "Диагностическое тело ответа скрыто.",
                unknown,
                "unknown status diagnostic"
            );
            AssertTrue(
                unknown.Length < 128,
                "diagnostic must remain bounded"
            );
            AssertTrue(
                unknown.IndexOf(
                    "C:\\private\\token",
                    StringComparison.Ordinal
                ) < 0,
                "diagnostic must not contain response values"
            );
        }

        private static void TestAutoCadCommandDiagnostics()
        {
            AutoCadCommandOperation[] operations =
            {
                AutoCadCommandOperation.AnalyzeModel,
                AutoCadCommandOperation.FindRemoteObject,
                AutoCadCommandOperation.ExportModel,
                AutoCadCommandOperation.DiscoverRoom,
                AutoCadCommandOperation.DiscoverRoomBoundaries,
                AutoCadCommandOperation.ExportRooms,
                AutoCadCommandOperation.SyncModel,
                AutoCadCommandOperation.SyncRooms
            };
            string[] commandNames =
            {
                "HA_ANALYZE_MODEL",
                "HA_FIND_REMOTE_OBJECT",
                "HA_EXPORT_MODEL",
                "HA_DISCOVER_ROOM",
                "HA_DISCOVER_ROOM_BOUNDARIES",
                "HA_EXPORT_ROOMS",
                "HA_SYNC_MODEL",
                "HA_SYNC_ROOMS"
            };

            for (int index = 0;
                 index < operations.Length;
                 index++)
            {
                string diagnostic =
                    AutoCadCommandDiagnostics.FormatUnexpected(
                        operations[index]
                    );

                AssertTrue(
                    diagnostic.StartsWith(
                        "\nКоманда " + commandNames[index] + " ",
                        StringComparison.Ordinal
                    ),
                    "unexpected diagnostic command mapping"
                );
                AssertTrue(
                    diagnostic.Length < 220,
                    "unexpected diagnostic must remain bounded"
                );
                AssertTrue(
                    diagnostic.IndexOf(
                        "C:\\private\\payload-token",
                        StringComparison.Ordinal
                    ) < 0,
                    "unexpected diagnostic must contain no caller values"
                );
            }

            AssertEqual(
                "AutoCAD не вычислил точную площадь/длину; " +
                "контур исключён из валидных границ.",
                AutoCadCommandDiagnostics
                    .FormatBoundaryMeasurementFailure(),
                "boundary measurement diagnostic"
            );

            bool invalidOperationRejected = false;
            try
            {
                AutoCadCommandDiagnostics.FormatUnexpected(
                    (AutoCadCommandOperation)999
                );
            }
            catch (ArgumentOutOfRangeException)
            {
                invalidOperationRejected = true;
            }
            AssertTrue(
                invalidOperationRejected,
                "invalid command operation must be rejected"
            );
        }

        private static void TestAutoCadSafeUserDiagnostics()
        {
            const string expected =
                "Сначала сохрани DWG на диск.";
            AutoCadCommandUserException safeException =
                new AutoCadCommandUserException(expected);

            AssertEqual(
                expected,
                safeException.SafeMessage,
                "safe user diagnostic"
            );

            string[] invalidMessages =
            {
                null,
                " ",
                new string(
                    'x',
                    AutoCadCommandUserException
                        .MaximumMessageLength + 1
                ),
                "first line\nsecond line"
            };

            for (int index = 0;
                 index < invalidMessages.Length;
                 index++)
            {
                bool rejected = false;
                try
                {
                    new AutoCadCommandUserException(
                        invalidMessages[index]
                    );
                }
                catch (ArgumentException)
                {
                    rejected = true;
                }

                AssertTrue(
                    rejected,
                    "unsafe user diagnostic must be rejected"
                );
            }
        }

        private static void TestRemoteHandleSelectionPlan()
        {
            RemoteHandleSelectionPlan plan =
                RemoteHandleSelectionPlan.Create(
                    new List<string>
                    {
                        " 1a ",
                        "1A",
                        null,
                        " ",
                        "0",
                        "-1",
                        "FFFFFFFFFFFFFFFF",
                        "2B"
                    }
                );

            AssertEqual(8, plan.TotalCount, "total Handle count");
            AssertEqual(
                5,
                plan.MalformedCount,
                "malformed Handle count"
            );
            AssertEqual(
                1,
                plan.DuplicateCount,
                "duplicate Handle count"
            );
            AssertEqual(
                2,
                plan.Candidates.Count,
                "unique Handle candidates"
            );
            AssertEqual(
                0,
                plan.Candidates[0].DiagnosticIndex,
                "first source index"
            );
            AssertEqual(
                26L,
                plan.Candidates[0].HandleValue,
                "first parsed Handle"
            );
            AssertEqual(
                7,
                plan.Candidates[1].DiagnosticIndex,
                "second source index"
            );
            AssertEqual(
                43L,
                plan.Candidates[1].HandleValue,
                "second parsed Handle"
            );
            AssertEqual(
                "\nПропущено Handle: некорректных — 5; " +
                "повторных — 1; не найдено в текущем DWG — 1.",
                plan.FormatSkippedSummary(1),
                "bounded skipped Handle summary"
            );
        }

        private static void TestAgentApiStartupRootPolicy()
        {
            string directory = CreateTestDirectory();

            try
            {
                string repositoryRoot =
                    Path.Combine(directory, "repository");
                string configuredRoot =
                    Path.Combine(directory, "configured");
                CreateAgentRoot(repositoryRoot);
                CreateAgentRoot(configuredRoot);

                string assemblyDirectory =
                    Path.Combine(
                        repositoryRoot,
                        "autocad-plugin",
                        "HomeAura.AutoCAD.Agent",
                        "bin",
                        "x64",
                        "Release"
                    );
                Directory.CreateDirectory(assemblyDirectory);

                AssertEqual(
                    new DirectoryInfo(repositoryRoot).FullName,
                    AgentApiStartupPolicy.ResolveAgentRoot(
                        null,
                        assemblyDirectory
                    ),
                    "assembly-parent root discovery"
                );
                AssertEqual(
                    new DirectoryInfo(configuredRoot).FullName,
                    AgentApiStartupPolicy.ResolveAgentRoot(
                        configuredRoot,
                        assemblyDirectory
                    ),
                    "explicit root override"
                );
                AssertEqual(
                    null,
                    AgentApiStartupPolicy.ResolveAgentRoot(
                        Path.Combine(directory, "missing"),
                        assemblyDirectory
                    ),
                    "invalid explicit root must fail closed"
                );
                AssertEqual(
                    null,
                    AgentApiStartupPolicy.ResolveAgentRoot(
                        "relative-root",
                        assemblyDirectory
                    ),
                    "relative explicit root must fail closed"
                );
                AssertEqual(
                    null,
                    AgentApiStartupPolicy.ResolveAgentRoot(
                        "bad\0root",
                        assemblyDirectory
                    ),
                    "invalid explicit root must fail closed"
                );
                AssertEqual(
                    Path.Combine(
                        configuredRoot,
                        ".venv",
                        "Scripts",
                        "python.exe"
                    ),
                    AgentApiStartupPolicy.GetPythonExecutable(
                        configuredRoot
                    ),
                    "Python executable path"
                );
            }
            finally
            {
                Directory.Delete(directory, true);
            }
        }

        private static void TestAgentApiStartupDiagnostics()
        {
            string rootMissing =
                AgentApiStartupPolicy.FormatFailure(
                    AgentApiStartupFailure.AgentRootMissing,
                    null
                );
            string pythonMissing =
                AgentApiStartupPolicy.FormatFailure(
                    AgentApiStartupFailure.PythonMissing,
                    null
                );
            string unexpected =
                AgentApiStartupPolicy.FormatFailure(
                    AgentApiStartupFailure.Unexpected,
                    null
                );

            AssertEqual(
                "Не найдена папка HomeAura Agent. " +
                "Задайте HOMEAURA_AGENT_ROOT.",
                rootMissing,
                "missing root diagnostic"
            );
            AssertEqual(
                "Не найден Python HomeAura " +
                "(.venv\\Scripts\\python.exe). " +
                "Создайте окружение по lock-файлам проекта.",
                pythonMissing,
                "missing Python diagnostic"
            );
            AssertEqual(
                "Не удалось запустить локальный процесс " +
                "HomeAura API.",
                AgentApiStartupPolicy.FormatFailure(
                    AgentApiStartupFailure.ProcessStartFailed,
                    null
                ),
                "process start diagnostic"
            );
            AssertEqual(
                "Процесс HomeAura API завершился при запуске " +
                "(код -1073741515).",
                AgentApiStartupPolicy.FormatFailure(
                    AgentApiStartupFailure.ProcessExited,
                    -1073741515
                ),
                "process exit diagnostic"
            );
            AssertEqual(
                "HomeAura API запущен, но не ответил за 8 секунд.",
                AgentApiStartupPolicy.FormatFailure(
                    AgentApiStartupFailure.ReadinessTimeout,
                    null
                ),
                "readiness timeout diagnostic"
            );
            AssertEqual(
                "Не удалось запустить HomeAura API " +
                "из-за локальной ошибки.",
                unexpected,
                "unexpected startup diagnostic"
            );
            AssertTrue(
                rootMissing.Length < 160 &&
                pythonMissing.Length < 160 &&
                unexpected.Length < 160,
                "startup diagnostics must remain bounded"
            );
            AssertTrue(
                rootMissing.IndexOf(
                    "C:\\private\\agent",
                    StringComparison.Ordinal
                ) < 0 &&
                unexpected.IndexOf(
                    "private-token",
                    StringComparison.Ordinal
                ) < 0,
                "startup diagnostics must not expose raw values"
            );

            bool invalidExitRejected = false;
            try
            {
                AgentApiStartupPolicy.FormatFailure(
                    AgentApiStartupFailure.Unexpected,
                    1
                );
            }
            catch (ArgumentException)
            {
                invalidExitRejected = true;
            }
            AssertTrue(
                invalidExitRejected,
                "unexpected exit code must be rejected"
            );
        }

        private static void CreateAgentRoot(string root)
        {
            string agentDirectory = Path.Combine(root, "agent");
            Directory.CreateDirectory(agentDirectory);
            File.WriteAllText(
                Path.Combine(agentDirectory, "api.py"),
                "# test marker",
                Encoding.UTF8
            );
        }

        private static void TestRemoteHandleSelectionValidation()
        {
            RemoteHandleSelectionPlan clean =
                RemoteHandleSelectionPlan.Create(
                    new List<string> { "A", "B" }
                );

            AssertEqual(
                string.Empty,
                clean.FormatSkippedSummary(0),
                "clean Handle summary"
            );

            bool countRejected = false;
            try
            {
                clean.FormatSkippedSummary(3);
            }
            catch (ArgumentOutOfRangeException)
            {
                countRejected = true;
            }
            AssertTrue(
                countRejected,
                "impossible not-found count must be rejected"
            );

            bool nullRejected = false;
            try
            {
                RemoteHandleSelectionPlan.Create(null);
            }
            catch (ArgumentNullException)
            {
                nullRejected = true;
            }
            AssertTrue(
                nullRejected,
                "null Handle list must be rejected"
            );
        }

        private static void TestAtomicWriterPreservesDestination()
        {
            string directory = CreateTestDirectory();
            string destination =
                Path.Combine(directory, "report.json");
            File.WriteAllText(destination, "old-report");

            try
            {
                bool failed = false;
                try
                {
                    AtomicFileWriter.Write(
                        destination,
                        delegate(Stream stream)
                        {
                            byte[] partial =
                                Encoding.UTF8.GetBytes("partial");
                            stream.Write(
                                partial,
                                0,
                                partial.Length
                            );
                            throw new InvalidOperationException(
                                "synthetic serialization failure"
                            );
                        }
                    );
                }
                catch (InvalidOperationException exception)
                {
                    failed = exception.Message ==
                        "synthetic serialization failure";
                }

                AssertTrue(
                    failed,
                    "writer exception must propagate"
                );
                AssertEqual(
                    "old-report",
                    File.ReadAllText(destination),
                    "failed write must preserve destination"
                );
                AssertNoAtomicTemporaryFiles(
                    directory,
                    destination
                );
            }
            finally
            {
                Directory.Delete(directory, true);
            }
        }

        private static void TestHistoryFirstPublicationOrder()
        {
            List<string> published = new List<string>();

            AtomicFileWriter.PublishHistoryThenCurrent(
                "history.json",
                "current.json",
                delegate(string path)
                {
                    published.Add(path);
                },
                delegate(string path)
                {
                    published.Add(path);
                }
            );

            AssertEqual(
                2,
                published.Count,
                "publication count"
            );
            AssertEqual(
                "history.json",
                published[0],
                "history publication must be first"
            );
            AssertEqual(
                "current.json",
                published[1],
                "current publication must be second"
            );
        }

        private static void TestHistoryFailurePreservesCurrent()
        {
            string directory = CreateTestDirectory();
            string history = Path.Combine(
                directory,
                "history.json"
            );
            string current = Path.Combine(
                directory,
                "current.json"
            );
            File.WriteAllText(history, "old-history");
            File.WriteAllText(current, "old-current");
            int currentPublisherCalls = 0;

            try
            {
                bool failed = false;
                try
                {
                    AtomicFileWriter.PublishHistoryThenCurrent(
                        history,
                        current,
                        delegate(string path)
                        {
                            AtomicFileWriter.WriteNew(
                                path,
                                delegate(Stream stream)
                                {
                                    byte[] bytes =
                                        Encoding.UTF8.GetBytes(
                                            "new-history"
                                        );
                                    stream.Write(
                                        bytes,
                                        0,
                                        bytes.Length
                                    );
                                }
                            );
                        },
                        delegate(string path)
                        {
                            currentPublisherCalls++;
                            WriteAtomicText(
                                path,
                                "new-current"
                            );
                        }
                    );
                }
                catch (IOException)
                {
                    failed = true;
                }

                AssertTrue(
                    failed,
                    "history collision must propagate"
                );
                AssertEqual(
                    0,
                    currentPublisherCalls,
                    "current publisher must not run"
                );
                AssertEqual(
                    "old-history",
                    File.ReadAllText(history),
                    "history collision must preserve archive"
                );
                AssertEqual(
                    "old-current",
                    File.ReadAllText(current),
                    "history collision must preserve current"
                );
                AssertNoAtomicTemporaryFiles(
                    directory,
                    history
                );
            }
            finally
            {
                Directory.Delete(directory, true);
            }
        }

        private static void TestAtomicWriterCreateOnlyPreservesDestination()
        {
            string directory = CreateTestDirectory();
            string destination =
                Path.Combine(directory, "archive.json");
            File.WriteAllText(destination, "old-archive");

            try
            {
                bool failed = false;
                try
                {
                    AtomicFileWriter.WriteNew(
                        destination,
                        delegate(Stream stream)
                        {
                            byte[] bytes =
                                Encoding.UTF8.GetBytes(
                                    "new-archive"
                                );
                            stream.Write(
                                bytes,
                                0,
                                bytes.Length
                            );
                        }
                    );
                }
                catch (IOException)
                {
                    failed = true;
                }

                AssertTrue(
                    failed,
                    "create-only collision must fail"
                );
                AssertEqual(
                    "old-archive",
                    File.ReadAllText(destination),
                    "create-only collision must preserve archive"
                );
                AssertNoAtomicTemporaryFiles(
                    directory,
                    destination
                );
            }
            finally
            {
                Directory.Delete(directory, true);
            }
        }

        private static string CreateTestDirectory()
        {
            string directory = Path.Combine(
                Path.GetTempPath(),
                "HomeAura.AtomicFileWriter." +
                Guid.NewGuid().ToString("N")
            );
            Directory.CreateDirectory(directory);
            return directory;
        }

        private static void WriteAtomicText(
            string destination,
            string value)
        {
            AtomicFileWriter.Write(
                destination,
                delegate(Stream stream)
                {
                    byte[] bytes = Encoding.UTF8.GetBytes(value);
                    stream.Write(bytes, 0, bytes.Length);
                }
            );
        }

        private static void AssertNoAtomicTemporaryFiles(
            string directory,
            string destination)
        {
            string pattern =
                "." + Path.GetFileName(destination) + ".*.tmp";
            AssertEqual(
                0,
                Directory.GetFiles(directory, pattern).Length,
                "atomic temporary files"
            );
        }

        private static void TestPolyline3dNonFiniteVertex()
        {
            List<RoomBoundaryVertex> source =
                Rectangle(0, 0, 4, 3);

            source[0].X = double.NaN;

            RoomBoundary boundary =
                Polyline3dBoundary(source, true);

            AssertFalse(
                boundary.Diagnostics.IsValid,
                "NaN coordinate must fail closed"
            );
            AssertEqual(
                3,
                boundary.SourceVertices.Count,
                "non-finite source vertex must not be published"
            );
            AssertFalse(
                boundary.ContourAreaM2.HasValue,
                "partial area must not be published"
            );
            AssertTrue(
                MessagesContain(boundary, "нечисловых"),
                "non-finite diagnostic"
            );
        }

        private static void TestPolyline3dNullVertex()
        {
            List<RoomBoundaryVertex> source =
                Rectangle(0, 0, 4, 3);

            source.Insert(2, null);

            RoomBoundary boundary =
                Polyline3dBoundary(source, true);

            AssertFalse(
                boundary.Diagnostics.IsValid,
                "null vertex must fail closed"
            );
            AssertEqual(
                4,
                boundary.SourceVertices.Count,
                "valid source vertices must remain available"
            );
            AssertFalse(
                boundary.ContourAreaM2.HasValue,
                "partial metrics must not be published"
            );
        }

        private static void TestPolyline3dNonFiniteUnits()
        {
            foreach (double factor in new[]
            {
                double.PositiveInfinity,
                double.Epsilon
            })
            {
                RoomBoundary boundary =
                    RoomGeometryMath.CreatePolyline3dBoundary(
                        "P3D",
                        "MAGIROOMBORDERS",
                        Rectangle(0, 0, 4, 3),
                        true,
                        "SimplePoly",
                        "Meters",
                        factor,
                        true
                    );

                AssertFalse(
                    boundary.Diagnostics.IsValid,
                    "unsafe unit factor must fail closed"
                );
                AssertFalse(
                    boundary.MetersPerDrawingUnit.HasValue,
                    "unsafe unit factor must not be published"
                );
                AssertFalse(
                    boundary.ContourAreaM2.HasValue,
                    "metric conversion must remain unavailable"
                );
            }
        }

        private static void TestPolyline3dMetricOverflow()
        {
            RoomBoundary boundary =
                Polyline3dBoundary(
                    Rectangle(
                        -double.MaxValue,
                        -double.MaxValue,
                        double.MaxValue,
                        double.MaxValue
                    ),
                    true
                );

            AssertFalse(
                boundary.Diagnostics.IsValid,
                "overflowing metrics must fail closed"
            );
            AssertFalse(
                boundary.ContourAreaM2.HasValue,
                "overflowing area must not be published"
            );
            AssertTrue(
                MessagesContain(boundary, "числовой диапазон"),
                "overflow diagnostic"
            );
        }

        private static void TestPolyline3dSelfIntersection()
        {
            RoomBoundary boundary =
                Polyline3dBoundary(
                    new List<RoomBoundaryVertex>
                    {
                        Vertex(0, 0),
                        Vertex(4, 4),
                        Vertex(0, 4),
                        Vertex(4, 0)
                    },
                    true
                );

            AssertFalse(
                boundary.Diagnostics.IsValid,
                "self-intersecting Polyline3d must fail"
            );
            AssertTrue(
                boundary.Diagnostics.IsSelfIntersecting,
                "self-intersection diagnostic"
            );
        }

        private static void TestPolyline3dMarkerOutside()
        {
            RoomBoundary boundary =
                Polyline3dBoundary(
                    Rectangle(0, 0, 4, 3),
                    true
                );

            AssertFalse(
                RoomGeometryMath.ContainsPoint(
                    boundary,
                    5,
                    1
                ),
                "outside marker must not match"
            );
        }

        private static void TestMagiCadBoundaryPriority()
        {
            RoomBoundary magiCadBoundary =
                Polyline3dBoundary(
                    Rectangle(0, 0, 5, 4),
                    true
                );

            magiCadBoundary.SourceHandle = "101DA95";
            magiCadBoundary.SourceLayer =
                "MAGIROOMBORDERS";
            magiCadBoundary.HasMagiCadData = true;

            RoomBoundary layerZero =
                ValidBoundary(
                    Rectangle(0, 0, 4.325, 4),
                    17.3
                );

            layerZero.SourceHandle = "101D22A";

            RoomBoundarySelectionResult selection =
                RoomGeometryMath
                    .RankContainingBoundaries(
                        new List<RoomBoundary>
                        {
                            layerZero,
                            magiCadBoundary
                        },
                        1,
                        1,
                        17.231460571289062
                    );

            AssertFalse(
                selection.IsAmbiguous,
                "different priority tiers"
            );
            AssertEqual(
                "101DA95",
                selection.Selected.SourceHandle,
                "MagiCAD boundary must win"
            );
        }

        private static void TestAreaMismatchWarning()
        {
            RoomBoundary boundary =
                Polyline3dBoundary(
                    Rectangle(
                        0,
                        0,
                        4.993328363,
                        3.990655762
                    ),
                    true
                );

            AssertEqual(
                "warning",
                RoomGeometryMath.GetAreaMatchStatus(
                    17.231460571289062,
                    boundary
                ),
                "more than 15 percent mismatch"
            );
        }

        private static RoomBoundary Polyline3dBoundary(
            List<RoomBoundaryVertex> vertices,
            bool closed)
        {
            return RoomGeometryMath
                .CreatePolyline3dBoundary(
                    "P3D",
                    "MAGIROOMBORDERS",
                    vertices,
                    closed,
                    "SimplePoly",
                    "Meters",
                    1,
                    true
                );
        }

        private static RoomBoundary ValidBoundary(
            List<RoomBoundaryVertex> vertices,
            double area)
        {
            RoomBoundary boundary =
                new RoomBoundary
                {
                    SourceHandle = "TEST",
                    SourceObjectType = "LWPOLYLINE",
                    SourceLayer = "0",
                    Vertices = vertices,
                    IsClosed = true,
                    ContourAreaM2 = area,
                    Direction =
                        RoomGeometryMath.GetDirection(
                            vertices
                        ),
                    DrawingUnits = "Meters",
                    MetersPerDrawingUnit = 1,
                    GeometrySource = "Test"
                };

            boundary.Diagnostics.IsSupported = true;
            boundary.Diagnostics.IsValid = true;
            boundary.Diagnostics
                .VertexToleranceDrawingUnits = 1e-9;
            boundary.Diagnostics
                .ArcChordToleranceDrawingUnits = 0.001;

            return boundary;
        }

        private static List<RoomBoundaryVertex>
            Rectangle(
                double minimumX,
                double minimumY,
                double maximumX,
                double maximumY)
        {
            return new List<RoomBoundaryVertex>
            {
                Vertex(minimumX, minimumY),
                Vertex(maximumX, minimumY),
                Vertex(maximumX, maximumY),
                Vertex(minimumX, maximumY)
            };
        }

        private static RoomBoundaryVertex Vertex(
            double x,
            double y,
            double bulge = 0)
        {
            return new RoomBoundaryVertex
            {
                X = x,
                Y = y,
                Z = 0,
                Bulge = bulge,
                SegmentType =
                    Math.Abs(bulge) <= 1e-12
                        ? "Line"
                        : "Arc"
            };
        }

        private static void Run(
            string name,
            Action test)
        {
            test();
            passed++;
            Console.WriteLine("ok - " + name);
        }

        private static bool MessagesContain(
            RoomBoundary boundary,
            string fragment)
        {
            foreach (string message
                     in boundary.Diagnostics.Messages)
            {
                if (message != null &&
                    message.IndexOf(
                        fragment,
                        StringComparison.OrdinalIgnoreCase
                    ) >= 0)
                {
                    return true;
                }
            }

            return false;
        }

        private static void AssertTrue(
            bool value,
            string message)
        {
            if (!value)
            {
                throw new InvalidOperationException(
                    message
                );
            }
        }

        private static void AssertFalse(
            bool value,
            string message)
        {
            AssertTrue(!value, message);
        }

        private static void AssertNear(
            double expected,
            double actual,
            double tolerance,
            string message)
        {
            if (Math.Abs(expected - actual) >
                tolerance)
            {
                throw new InvalidOperationException(
                    message +
                    ": expected " +
                    expected +
                    ", actual " +
                    actual
                );
            }
        }

        private static void AssertEqual<T>(
            T expected,
            T actual,
            string message)
        {
            if (!EqualityComparer<T>
                    .Default.Equals(
                        expected,
                        actual
                    ))
            {
                throw new InvalidOperationException(
                    message +
                    ": expected " +
                    expected +
                    ", actual " +
                    actual
                );
            }
        }
    }
}
