import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const sourcePath = "C:/Users/Idaho_S/Documents/Codex/2026-08-30/n/work/db_export.json";
const outputPath = "C:/Users/Idaho_S/Documents/Codex/2026-08-30/n/outputs/nuclear-literature-database.xlsx";
const stableOutputPath = "C:/Users/Idaho_S/Documents/Codex/nuclear-literature-db/exports/nuclear-literature.xlsx";
const previewDir = "C:/Users/Idaho_S/Documents/Codex/2026-08-30/n/work/workbook-previews";
const data = JSON.parse(await fs.readFile(sourcePath, "utf8"));
const latestRunDate = data.runs.length ? data.runs[0].run_id : new Date().toISOString().slice(0, 10);

const workbook = Workbook.create();
const dashboard = workbook.worksheets.add("Dashboard");
const papersSheet = workbook.worksheets.add("Papers");
const runsSheet = workbook.worksheets.add("Collection Runs");
const topicsSheet = workbook.worksheets.add("Topics");
const linksSheet = workbook.worksheets.add("Paper Topics");

const navy = "#17324D";
const blue = "#2166AC";
const paleBlue = "#EAF2F8";
const paleGray = "#F4F6F7";
const border = "#D5DCE3";
const white = "#FFFFFF";
const green = "#1B7F5A";

for (const sheet of [dashboard, papersSheet, runsSheet, topicsSheet, linksSheet]) {
  sheet.showGridLines = false;
}

function dateValue(value) {
  return value ? new Date(`${value}T00:00:00`) : null;
}

function styleDataSheet(sheet, headerRange, usedRange, widths) {
  headerRange.format = {
    fill: navy,
    font: { bold: true, color: white },
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: navy },
  };
  headerRange.format.rowHeight = 32;
  usedRange.format.borders = { insideHorizontal: { style: "thin", color: border } };
  widths.forEach(([column, width]) => { sheet.getRange(`${column}:${column}`).format.columnWidth = width; });
  sheet.freezePanes.freezeRows(1);
}

const paperHeaders = [
  "DOI", "Title EN", "Title KO", "Journal", "ISSN", "Authors", "DOI Registered", "Published Online", "Issue Date",
  "Document Type", "Primary Topic", "Abstract", "Abstract URL", "DOI URL", "Open Access", "First Seen", "Last Checked", "Status", "Source"
];
const paperRows = data.papers.map((p) => [
  p.doi, p.title_en, p.title_ko || "", p.journal, p.issn || "", p.authors || "", dateValue(p.doi_registered_date),
  dateValue(p.published_online), dateValue(p.issue_date), p.document_type, p.primary_topic, p.abstract || "", p.abstract_url || "",
  p.doi_url, Boolean(p.open_access), dateValue(p.first_seen), dateValue(p.last_checked), p.status, p.source,
]);
papersSheet.getRangeByIndexes(0, 0, 1, paperHeaders.length).values = [paperHeaders];
papersSheet.getRangeByIndexes(1, 0, paperRows.length, paperHeaders.length).values = paperRows;
const papersLastRow = paperRows.length + 1;
papersSheet.tables.add(`A1:S${papersLastRow}`, true, "PapersTable");
styleDataSheet(papersSheet, papersSheet.getRange("A1:S1"), papersSheet.getRange(`A1:S${papersLastRow}`), [
  ["A", 30], ["B", 58], ["C", 45], ["D", 34], ["E", 15], ["F", 42], ["G", 15], ["H", 15], ["I", 15],
  ["J", 15], ["K", 20], ["L", 65], ["M", 42], ["N", 38], ["O", 12], ["P", 14], ["Q", 14], ["R", 13], ["S", 28],
]);
papersSheet.getRange(`B2:C${papersLastRow}`).format.wrapText = true;
papersSheet.getRange(`F2:F${papersLastRow}`).format.wrapText = true;
papersSheet.getRange(`G2:I${papersLastRow}`).format.numberFormat = "yyyy-mm-dd";
papersSheet.getRange(`P2:Q${papersLastRow}`).format.numberFormat = "yyyy-mm-dd";

const runHeaders = ["Run ID", "Period Start", "Period End", "Executed At", "Found", "New", "Updated", "Errors", "Source Note"];
const runRows = data.runs.map((r) => [r.run_id, dateValue(r.period_start), dateValue(r.period_end), r.executed_at, r.found_count, r.new_count, r.updated_count, r.error_count, r.source_note]);
runsSheet.getRangeByIndexes(0, 0, 1, runHeaders.length).values = [runHeaders];
runsSheet.getRangeByIndexes(1, 0, runRows.length, runHeaders.length).values = runRows;
const runsLastRow = runRows.length + 1;
runsSheet.tables.add(`A1:I${runsLastRow}`, true, "CollectionRunsTable");
styleDataSheet(runsSheet, runsSheet.getRange("A1:I1"), runsSheet.getRange(`A1:I${runsLastRow}`), [["A", 16], ["B", 15], ["C", 15], ["D", 24], ["E", 12], ["F", 12], ["G", 12], ["H", 12], ["I", 46]]);
runsSheet.getRange(`B2:C${runsLastRow}`).format.numberFormat = "yyyy-mm-dd";

const topicHeaders = ["Topic ID", "Topic KO", "Keywords", "Active"];
const topicRows = data.topics.map((t) => [t.topic_id, t.topic_ko, t.keywords, Boolean(t.active)]);
topicsSheet.getRangeByIndexes(0, 0, 1, topicHeaders.length).values = [topicHeaders];
topicsSheet.getRangeByIndexes(1, 0, topicRows.length, topicHeaders.length).values = topicRows;
const topicsLastRow = topicRows.length + 1;
topicsSheet.tables.add(`A1:D${topicsLastRow}`, true, "TopicsTable");
styleDataSheet(topicsSheet, topicsSheet.getRange("A1:D1"), topicsSheet.getRange(`A1:D${topicsLastRow}`), [["A", 12], ["B", 24], ["C", 85], ["D", 12]]);
topicsSheet.getRange(`C2:C${topicsLastRow}`).format.wrapText = true;

const linkHeaders = ["DOI", "Topic KO", "Primary"];
const linkRows = data.paper_topics.map((t) => [t.doi, t.topic_ko, Boolean(t.is_primary)]);
linksSheet.getRangeByIndexes(0, 0, 1, linkHeaders.length).values = [linkHeaders];
linksSheet.getRangeByIndexes(1, 0, linkRows.length, linkHeaders.length).values = linkRows;
const linksLastRow = linkRows.length + 1;
linksSheet.tables.add(`A1:C${linksLastRow}`, true, "PaperTopicsTable");
styleDataSheet(linksSheet, linksSheet.getRange("A1:C1"), linksSheet.getRange(`A1:C${linksLastRow}`), [["A", 34], ["B", 24], ["C", 12]]);

dashboard.getRange("A1:H2").merge();
dashboard.getRange("A1").values = [["Nuclear Literature Database"]];
dashboard.getRange("A1:H2").format = { fill: navy, font: { bold: true, color: white, size: 20 }, verticalAlignment: "center" };
dashboard.getRange("A3:H3").merge();
dashboard.getRange("A3").values = [[`Five journals · DOI-registered publications · Updated ${latestRunDate}`]];
dashboard.getRange("A3:H3").format = { fill: paleBlue, font: { color: navy, italic: true } };

dashboard.getRange("A5:A8").values = [["Total papers"], ["Collection runs"], ["Research articles"], ["Open access"]];
dashboard.getRange("B5").formulas = [[`=COUNTA('Papers'!$A$2:$A$${papersLastRow})`]];
dashboard.getRange("B6").formulas = [[`=COUNTA('Collection Runs'!$A$2:$A$${runsLastRow})`]];
dashboard.getRange("B7").formulas = [[`=COUNTIF('Papers'!$J$2:$J$${papersLastRow},"연구논문")`]];
dashboard.getRange("B8").formulas = [[`=COUNTIF('Papers'!$O$2:$O$${papersLastRow},TRUE)`]];
dashboard.getRange("A5:B8").format = { fill: paleGray, borders: { preset: "outside", style: "thin", color: border } };
dashboard.getRange("A5:A8").format.font = { bold: true, color: navy };
dashboard.getRange("B5:B8").format = { font: { bold: true, color: blue, size: 16 }, horizontalAlignment: "right", numberFormat: "#,##0" };

dashboard.getRange("D5:E5").values = [["Document type", "Count"]];
const typeOrder = ["연구논문", "리뷰·관점", "편집물", "정오표"];
dashboard.getRange("D6:D9").values = typeOrder.map((v) => [v]);
dashboard.getRange("E6").formulas = [[`=COUNTIF('Papers'!$J$2:$J$${papersLastRow},D6)`]];
dashboard.getRange("E6:E9").fillDown();
dashboard.getRange("D5:E9").format.borders = { insideHorizontal: { style: "thin", color: border } };
dashboard.getRange("D5:E5").format = { fill: navy, font: { bold: true, color: white } };

dashboard.getRange("A11:B11").values = [["Journal", "Papers"]];
const journalNames = data.journal_summary.map((x) => x.journal);
dashboard.getRangeByIndexes(11, 0, journalNames.length, 1).values = journalNames.map((v) => [v]);
dashboard.getRange("B12").formulas = [[`=COUNTIF('Papers'!$D$2:$D$${papersLastRow},A12)`]];
dashboard.getRange(`B12:B${11 + journalNames.length}`).fillDown();
dashboard.getRange(`A11:B${11 + journalNames.length}`).format.borders = { insideHorizontal: { style: "thin", color: border } };
dashboard.getRange("A11:B11").format = { fill: navy, font: { bold: true, color: white } };

dashboard.getRange("D11:E11").values = [["Primary topic", "Papers"]];
const topicNames = data.topic_summary.map((x) => x.primary_topic);
dashboard.getRangeByIndexes(11, 3, topicNames.length, 1).values = topicNames.map((v) => [v]);
dashboard.getRange("E12").formulas = [[`=COUNTIF('Papers'!$K$2:$K$${papersLastRow},D12)`]];
dashboard.getRange(`E12:E${11 + topicNames.length}`).fillDown();
dashboard.getRange(`D11:E${11 + topicNames.length}`).format.borders = { insideHorizontal: { style: "thin", color: border } };
dashboard.getRange("D11:E11").format = { fill: navy, font: { bold: true, color: white } };

dashboard.getRange("G11:H11").values = [["Period end", "Found"]];
dashboard.getRangeByIndexes(11, 6, runRows.length, 1).formulas = runRows.map((_, i) => [`='Collection Runs'!C${i + 2}`]);
dashboard.getRangeByIndexes(11, 7, runRows.length, 1).formulas = runRows.map((_, i) => [`='Collection Runs'!E${i + 2}`]);
dashboard.getRange(`G12:G${11 + runRows.length}`).format.numberFormat = "yyyy-mm-dd";
dashboard.getRange(`G11:H${11 + runRows.length}`).format.borders = { insideHorizontal: { style: "thin", color: border } };
dashboard.getRange("G11:H11").format = { fill: navy, font: { bold: true, color: white } };

const journalChart = dashboard.charts.add("bar", dashboard.getRange(`A11:B${11 + journalNames.length}`));
journalChart.title = "Papers by journal";
journalChart.hasLegend = false;
journalChart.xAxis = { axisType: "textAxis" };
journalChart.yAxis = { numberFormatCode: "#,##0" };
journalChart.setPosition("J2", "Q16");

const topicChart = dashboard.charts.add("bar", dashboard.getRange(`D11:E${11 + topicNames.length}`));
topicChart.title = "Papers by primary topic";
topicChart.hasLegend = false;
topicChart.xAxis = { axisType: "textAxis" };
topicChart.yAxis = { numberFormatCode: "#,##0" };
topicChart.setPosition("J18", "Q36");

const runChart = dashboard.charts.add("line", dashboard.getRange(`G11:H${11 + runRows.length}`));
runChart.title = "Papers collected per run";
runChart.hasLegend = false;
runChart.xAxis = { axisType: "textAxis" };
runChart.yAxis = { numberFormatCode: "#,##0" };
runChart.setPosition("A23", "H36");

dashboard.getRange("A38:H40").merge();
dashboard.getRange("A38").values = [["Data source: Crossref DOI created date and publisher metadata. DOI is the unique key. Edit review status only in the Papers sheet; automated refreshes preserve the database as the authoritative source."]];
dashboard.getRange("A38:H40").format = { fill: paleBlue, font: { color: navy, italic: true }, wrapText: true, verticalAlignment: "center" };
dashboard.getRange("A:H").format.columnWidth = 20;
dashboard.getRange("A:A").format.columnWidth = 34;
dashboard.getRange("D:D").format.columnWidth = 28;
dashboard.getRange("G:G").format.columnWidth = 18;
dashboard.freezePanes.freezeRows(3);

await fs.mkdir(previewDir, { recursive: true });
for (const [sheetName, range] of [
  ["Dashboard", "A1:H20"], ["Papers", "A1:S14"], ["Collection Runs", `A1:I${runsLastRow}`], ["Topics", `A1:D${topicsLastRow}`], ["Paper Topics", "A1:C16"],
]) {
  const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
  await fs.writeFile(`${previewDir}/${sheetName.replaceAll(" ", "-")}.png`, new Uint8Array(await preview.arrayBuffer()));
}

const dashboardCheck = await workbook.inspect({ kind: "table", range: "Dashboard!A1:H20", include: "values,formulas", tableMaxRows: 20, tableMaxCols: 8 });
console.log(dashboardCheck.ndjson);
const errorCheck = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 300 }, summary: "final formula error scan" });
console.log(errorCheck.ndjson);

await fs.mkdir("C:/Users/Idaho_S/Documents/Codex/2026-08-30/n/outputs", { recursive: true });
await fs.mkdir("C:/Users/Idaho_S/Documents/Codex/nuclear-literature-db/exports", { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
await fs.copyFile(outputPath, stableOutputPath);
console.log(JSON.stringify({ outputPath, stableOutputPath, papers: paperRows.length, runs: runRows.length }));
