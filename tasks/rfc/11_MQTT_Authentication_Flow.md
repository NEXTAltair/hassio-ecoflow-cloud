# hassio-ecoflow-cloud MQTT認証フロー解説

## 1. 概要

このドキュメントは、`hassio-ecoflow-cloud` カスタムコンポーネントがEcoFlowデバイスとMQTTブローカーを介して通信する際の認証情報の取得および利用フローについて解説します。
特に、ユーザーが設定画面で入力する情報（メールアドレス、パスワード）から、実際にMQTT接続に使用される詳細な認証情報（MQTTユーザー名、MQTTパスワード、ClientIDなど）がどのように導出・生成されるかを明らかにします。

## 2. 認証フロー (Manual Setup / `EcoflowPrivateApiClient` 使用時)

ユーザーがHome AssistantのUIから「Manual Setup」を選択し、EcoFlowアカウントのメールアドレスとパスワードを入力した場合の認証処理の流れは以下の通りです。

1.  **ユーザー入力情報の取得**
    *   `ecoflow_username`: ユーザーが入力したEcoFlowアカウントのメールアドレス。
    *   `ecoflow_password`: ユーザーが入力したEcoFlowアカウントのパスワード。

2.  **EcoFlow認証APIへのログイン (`/auth/login`)**
    *   `EcoflowPrivateApiClient` が、上記メールアドレスとBase64エンコードされたパスワードを使用し、EcoFlowの認証エンドポイント (`https://{api_domain}/auth/login`) にPOSTリクエストを送信します。
    *   このAPI呼び出しにより、以下の情報を取得します。
        *   **認証トークン (`token`)**: EcoFlow APIへの後続アクセスのために使用されるBearerトークン。
        *   **ユーザーID (`userId`)**: EcoFlowシステム内でユーザーを一意に識別するID（19桁の数字など）。

3.  **EcoFlow IoT認証APIからのMQTT接続情報取得 (`/iot-auth/app/certification`)**
    *   `EcoflowPrivateApiClient` が、ステップ2で取得した認証トークンと`userId`を使用し、EcoFlowのIoT認証エンドポイント (`https://{api_domain}/iot-auth/app/certification`) にGETリクエストを送信します。
    *   このAPI呼び出しにより、`EcoflowApiClient`の`_accept_mqqt_certification`メソッドを介して、以下のMQTT接続情報が取得され、`EcoflowMqttInfo`オブジェクトに格納されます。
        *   `url`: MQTTブローカーのホスト名またはIPアドレス。
        *   `port`: MQTTブローカーのポート番号。
        *   `certificateAccount`: MQTT接続時に使用される **MQTTユーザー名**。
        *   `certificatePassword`: MQTT接続時に使用される **MQTTパスワード**。
        *   `certificate_ca`: (コード上では取得しているが、`EcoflowMqttInfo` には直接格納されていない模様。MQTTクライアント初期化時に別途利用される可能性あり。)

4.  **ClientIDのクライアントサイド生成**
    *   `EcoflowPrivateApiClient` が、以下の形式でMQTT接続用の**ClientID**を生成し、`EcoflowMqttInfo`オブジェクトの`client_id`フィールドに設定します。
        *   形式: `ANDROID_{ランダムなUUID（大文字）}_{userId}`
        *   例: `ANDROID_A1B2C3D4E5F67890A1B2C3D4E5F67890_1234567890123456789`

5.  **MQTTクライアントの初期化と接続**
    *   `EcoflowApiClient`の`start()`メソッド内で`EcoflowMQTTClient`が初期化されます。
    *   初期化時には、`EcoflowMqttInfo`オブジェクトに格納された上記の情報（MQTTブローカーURL、ポート、MQTTユーザー名、MQTTパスワード、生成されたClientID）が使用され、EcoFlowのMQTTブローカーへの接続が試行されます。

## 3. 各認証情報の対応と意味

一般的にEcoFlowのMQTT連携で言及される認証項目と、`hassio-ecoflow-cloud`内部での対応は以下の通りです。

*   **`UserName` (または `mqtt_username`)**:
    *   **対応:** `certificateAccount` (IoT認証APIから取得)
    *   **意味:** MQTTブローカーへの接続に使用されるユーザー名。
*   **`UserID`**:
    *   **対応:** `userId` (認証APIから取得)
    *   **意味:** EcoFlowアカウントのユーザー識別子。MQTTトピックのパス構築やClientIDの一部として利用。
*   **`UserPassword` (または `mqtt_password`)**:
    *   **対応:** `certificatePassword` (IoT認証APIから取得)
    *   **意味:** MQTTブローカーへの接続に使用されるパスワード。
*   **`ClientID`**:
    *   **対応:** `ANDROID_{UUID}_{userId}` (クライアントサイドで生成)
    *   **意味:** MQTT接続において、このHome Assistantインテグレーションインスタンスを一意に識別するためのID。

## 4. まとめ

`hassio-ecoflow-cloud`では、ユーザーが提供するシンプルな認証情報（メールアドレスとパスワード）を元に、EcoFlowの各種APIを通じてMQTT接続に必要な詳細な認証情報を動的に取得・生成しています。これにより、ユーザーは複雑な認証情報を意識することなく、比較的容易に連携設定を行うことができますが、内部ではセキュリティと識別性を確保するための多段階の認証フローが実行されています。