const loremIpsum = require("lorem-ipsum")

const numberOfMissions = 30

const sqls = Array.from(Array(numberOfMissions).keys())
	.map(missionId => {
		const heading = loremIpsum.loremIpsum({ count: 1, units: "sentence" }).replace(/[\r\n]+/g, "");
		const description = loremIpsum.loremIpsum({ count: 5, units: "paragraphs" }).replace(/[\r\n]+/g, "\\n");

		return `INSERT INTO missions (mission, description, heading) VALUES ('sts-${missionId}', '${description}', '${heading}');`
	})
	.join("\n")

console.log(sqls)