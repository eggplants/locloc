      const headerTexts = ["languages", "lines", "blanks", "code", "files", "comments"];

      const escapeHTML = (unsafeText) => (
        unsafeText.replace(/[&<"']/g, (m) => {
          switch (m) {
          case '&':
            return '&amp;';
          case '<':
            return '&lt;';
          case '"':
            return '&quot;';
          default:
            return '&#039;';
          }
        })
      );

      const getLocData = async (url, branch) => {
        const endpoint = new URL(`${window.origin}/res?url=${url}&branch=${branch}`)
        const response = await fetch(endpoint, {
          method: "GET",
          mode: "same-origin",
          cache: "no-cache",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
          },
          redirect: "follow",
          referrerPolicy: "no-referrer",
        });
        return {res: response, body: await response.json()};
      }
      const updateResult = () => {
        const url = encodeURIComponent(document.getElementById("url").value);
        const branch = encodeURIComponent(document.getElementById("branch").value);
        if (!url) return;

        const resultElm = document.getElementById("result");
        const errorElm = document.getElementById("error");
        const formElm = document.getElementById("form_fieldset");

        errorElm.innerText = "Loading...";
        formElm.disabled = true;

        getLocData(url, branch)
          .then(({res, body}) => {
            formElm.disabled = false;
            if(res.status !== 200){
              errorElm.innerText = `${res.status} ${res.statusText}`;
            } else {
              errorElm.innerText = "";
              const tableElm = document.createElement("table");

              const theadElm = document.createElement("thead");
              const theadTrElm = document.createElement("tr");
              headerTexts.forEach(headerText => {
                const theadThElm = document.createElement("th");
                theadThElm.innerText = headerText;
                theadTrElm.appendChild(theadThElm);
              })
              theadElm.appendChild(theadTrElm);
              tableElm.appendChild(theadElm);

              const tbodyElm = document.createElement("tbody");
              Object.keys(body.result).forEach(languageText => {
                const total = body.result[languageText];
                const tbodyTrElm = document.createElement("tr");
                const tbodyThElm = document.createElement("th");
                tbodyThElm.innerText = languageText;
                tbodyTrElm.appendChild(tbodyThElm);

                headerTexts.slice(1).forEach(headerText => {
                  const tbodyTdElm = document.createElement("td");
                  tbodyTdElm.innerText = total[headerText];
                  tbodyTrElm.appendChild(tbodyTdElm);
                });
                tbodyElm.appendChild(tbodyTrElm);
              });
              tableElm.appendChild(tbodyElm);

              const tfootElm = document.createElement("tfoot");
              const tfootTrElm = document.createElement("tr");
              const tfootThElm = document.createElement("th");
              tfootThElm.innerText = "Total";
              tfootTrElm.appendChild(tfootThElm);

              headerTexts.slice(1).forEach(headerText => {
                const tfootTdElm = document.createElement("td");
                tfootTdElm.innerText = body.total[headerText];
                tfootTrElm.appendChild(tfootTdElm);
              })
              tfootElm.appendChild(tfootTrElm);
              tableElm.appendChild(tfootElm);

              const tableCaptionElm = document.createElement("caption");
              const repoUrl = decodeURIComponent(url);
              tableCaptionElm.innerHTML = [
                `Repo: <a href="${repoUrl}">${repoUrl}</a>`,
                `, Branch: ${escapeHTML(branch || "(empty)")}</div>`,
              ].join("");

              tableElm.appendChild(tableCaptionElm);

              if(document.getElementsByTagName("table").length > 0) {
                resultElm.appendChild(document.createElement("hr"));
              };
              resultElm.appendChild(tableElm);
            }
          }
        );
      };
