import main as app
import mockchimp3
import mock_sheet
app.mailchimp3 = mockchimp3
app.build = mock_sheet.build


def test_add_report(capsys):
    sheet_id = 'apple-3fd'
    mock_spreadsheet = mock_sheet.GSheetValues()
    master_sheet = mock_spreadsheet._sheets['master']
    test1_sheet = mock_spreadsheet._sheets['test1']
    transposed = list(zip(*master_sheet))
    open_rate = mockchimp3._reports['opens']['open_rate']
    click_rate = mockchimp3._reports['clicks']['click_rate']
    urls_clicked = mockchimp3._click_details['urls_clicked']

    app.main(['Test1', '--to-google-sheet', sheet_id])

    assert (
        'Test1' in transposed[8][10:16]
        and open_rate == test1_sheet[1][1]
        and click_rate == test1_sheet[2][1]
        and _is_equal(urls_clicked[0], test1_sheet[5])
        and _is_equal(urls_clicked[1], test1_sheet[6])
    )


def _is_equal(url_clicked_info, sheet_row_data):
    return (
        url_clicked_info['url'] == sheet_row_data[2]
        and url_clicked_info['click_percentage'] == sheet_row_data[3]
        and url_clicked_info['unique_click_percentage'] == sheet_row_data[4]
    )
