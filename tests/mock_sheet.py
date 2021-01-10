def build(*args, **kwargs):
    return GSheetClient()


class GSheetClient:
    def spreadsheets(self):
        return GSheetSpreadsheets()


class GSheetSpreadsheets:
    def values(self):
        return GSheetValues()


class GSheetValues:
    _sheets = {
        'master': [13 * [''] for i in range(40)],
        'test1': [13 * [''] for i in range(40)],
    }

    def batchGet(self, *, spreadsheetId, ranges, majorDimension='ROWS'):
        def func():
            response = {'valueRanges': [], 'spreadsheetId': spreadsheetId}
            valueRanges = response['valueRanges']
            for r in ranges:
                sheet_name, cell_range = r.split('!')
                start, end = cell_range.split(':')
                start_col, start_row = ord(start[0])-65, int(start[1:])-1
                end_col, end_row = ord(end[0])-65, int(end[1:])-1

                target_sheet = self._sheets[sheet_name.lower()]
                results = []
                for i in range(start_row, end_row+1):
                    results.append([])
                    row = results[-1]
                    for j in range(start_col, end_col+1):
                        row.append(target_sheet[i][j])

                valueRanges.append({
                    'range': r,
                    'majorDimension': majorDimension,
                })
                if majorDimension == 'COLUMNS':
                    valueRanges[-1]['values'] = list(zip(*results))
                else:
                    valueRanges[-1]['values'] = results
            return response
        return Request(func)

    def batchUpdate(self, *, spreadsheetId, body):
        def func():
            for mod in body['data']:
                range_, values = mod['range'], mod['values']
                majorDimension = mod.get('majorDimension', 'ROWS')

                sheet_name, cell_range = range_.split('!')
                start, end = cell_range.split(':')
                start_col, start_row = ord(start[0])-65, int(start[1:])-1
                end_col, end_row = ord(end[0])-65, int(end[1:])-1

                results = []
                for i in range(start_row, end_row+1):
                    results.append([(i, j) for j in range(start_col, end_col+1)])

                if majorDimension == 'COLUMNS':
                    results = list(zip(*results))

                target_sheet = self._sheets[sheet_name.lower()]
                width = len(results[0])
                for i in range(len(results)):
                    for j in range(width):
                        x, y = results[i][j]
                        try:
                            target_sheet[x][y] = values[i][j]
                        except IndexError:
                            break
                    if i >= len(values):
                        break
        return Request(func)

    def append(self, *, spreadsheetId, range, body, valueInputOption=None):
        def func():
            values = body['values']
            sheet_name, cell_range = range.split('!')
            start, end = cell_range.split(':')
            start_col, start_row = ord(start[0])-65, int(start[1:])-1
            end_col, end_row = ord(end[0])-65, int(end[1:])-1

            target_sheet = self._sheets[sheet_name.lower()]
            insertion_row = None
            for i in self._og_range(start_row, end_row+1):
                for j in self._og_range(start_col, end_col+1):
                    if target_sheet[i][j] != '':
                        break
                else:
                    insertion_row = i
                    break

            if insertion_row is None:
                return
            results = []
            for i in self._og_range(insertion_row, end_row+1):
                results.append([(i, j) for j in self._og_range(start_col, end_col+1)])

            width = len(results[0])
            for i in self._og_range(len(results)):
                for j in self._og_range(width):
                    x, y = results[i][j]
                    try:
                        target_sheet[x][y] = values[i][j]
                    except IndexError:
                        break
                if i >= len(values):
                    break

        return Request(func)

    @staticmethod
    def _og_range(*args, **kwargs):
        return range(*args, **kwargs)


class Request:

    def __init__(self, func):
        self._func = func

    def execute(self):
        return self._func()
