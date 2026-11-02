from app.core.config import Settings


def test_aiven_service_uri_is_accepted_as_is():
    settings = Settings(
        database_url="mysql://avnadmin:s3nh@mysql-x.aivencloud.com:12345/defaultdb?ssl-mode=REQUIRED"
    )
    assert settings.database_url == (
        "mysql+pymysql://avnadmin:s3nh@mysql-x.aivencloud.com:12345/defaultdb?charset=utf8mb4"
    )


def test_sqlalchemy_url_is_kept():
    url = "mysql+pymysql://u:p@localhost:3306/eventmer?charset=utf8mb4"
    assert Settings(database_url=url).database_url == url


def test_pasted_gmail_values_are_cleaned():
    settings = Settings(
        gmail_client_id='  "123-abc.apps.googleusercontent.com"\n',
        gmail_refresh_token=" 1//token ",
    )
    assert settings.gmail_client_id == "123-abc.apps.googleusercontent.com"
    assert settings.gmail_refresh_token == "1//token"
